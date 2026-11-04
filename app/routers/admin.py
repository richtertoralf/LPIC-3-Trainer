"""Administration: users, settings, content import, question management and groups."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.content import ContentError, import_document, parse_json_bytes
from app.deps import (
    SETTING_REGISTRATION,
    get_db,
    get_setting,
    require_admin,
    require_supervisor,
    set_setting,
)
from app.models import (
    ROLE_LEARNER,
    ROLES,
    STATUS_ACTIVE,
    STATUS_DISABLED,
    STATUS_PENDING,
    Attempt,
    Exam,
    Group,
    GroupMember,
    GroupSource,
    ImportBatch,
    Lab,
    Module,
    Question,
    Term,
    User,
    UserModule,
)
from app.routers.auth import USERNAME_RE
from app.security import MIN_PASSWORD_LENGTH, delete_user_sessions, hash_password
from app.services import all_modules, module_progress, set_batch_release
from app.web import redirect, render

router = APIRouter(prefix="/admin")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


# -------------------------------------------------------------------- overview


@router.get("")
def overview(
    request: Request, user: User = Depends(require_supervisor), db: Session = Depends(get_db)
):
    counts = {
        "users": db.execute(select(func.count(User.id))).scalar_one(),
        "pending": db.execute(
            select(func.count(User.id)).where(User.status == STATUS_PENDING)
        ).scalar_one(),
        "questions": db.execute(select(func.count(Question.id))).scalar_one(),
        "terms": db.execute(select(func.count(Term.id))).scalar_one(),
        "labs": db.execute(select(func.count(Lab.id))).scalar_one(),
        "groups": db.execute(select(func.count(Group.id))).scalar_one(),
        "exams": db.execute(
            select(func.count(Exam.id)).where(Exam.finished_at.is_not(None))
        ).scalar_one(),
    }
    return render(
        request,
        "admin/overview.html",
        {"counts": counts, "registration_mode": get_setting(db, SETTING_REGISTRATION)},
    )


# ----------------------------------------------------------------------- users


@router.get("/users")
def users(
    request: Request, user: User = Depends(require_supervisor), db: Session = Depends(get_db)
):
    """Administrators see everybody; supervisors see pending accounts and their own members."""
    stmt = select(User).order_by(User.status, User.username)
    if not user.is_admin:
        my_groups = select(GroupMember.group_id).where(
            GroupMember.user_id == user.id, GroupMember.role == "supervisor"
        )
        members = select(GroupMember.user_id).where(GroupMember.group_id.in_(my_groups))
        stmt = stmt.where(
            or_(User.status == STATUS_PENDING, User.id.in_(members), User.id == user.id)
        )
    rows = list(db.execute(stmt).scalars())
    return render(request, "admin/users.html", {"users": rows, "roles": ROLES})


@router.post("/users")
def create_user(
    username: str = Form(...),
    display_name: str = Form(""),
    role: str = Form(ROLE_LEARNER),
    password: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create an active account from the web interface (P2-2)."""
    username = username.strip().lower()
    if not USERNAME_RE.match(username):
        return redirect(
            "/admin/users", "Ungültiger Benutzername (3 bis 32 Zeichen, a-z, 0-9, . - _).", "error"
        )
    if role not in ROLES:
        raise HTTPException(400, "Ungültige Rolle")
    if len(password) < MIN_PASSWORD_LENGTH:
        return redirect(
            "/admin/users",
            f"Das Passwort braucht mindestens {MIN_PASSWORD_LENGTH} Zeichen.",
            "error",
        )
    if db.execute(select(User.id).where(User.username == username)).scalar_one_or_none():
        return redirect("/admin/users", "Dieser Benutzername ist bereits vergeben.", "error")
    db.add(
        User(
            username=username,
            display_name=display_name.strip()[:128],
            password_hash=hash_password(password),
            role=role,
            status=STATUS_ACTIVE,
        )
    )
    return redirect("/admin/users", f"Benutzer {username} ({role}) angelegt.", "success")


@router.post("/users/{user_id}/approve")
def approve_user(
    user_id: int, user: User = Depends(require_supervisor), db: Session = Depends(get_db)
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Benutzer nicht gefunden")
    target.status = STATUS_ACTIVE
    db.add(target)
    return redirect("/admin/users", f"{target.username} freigegeben.", "success")


@router.post("/users/{user_id}/status")
def set_user_status(
    user_id: int,
    status: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Benutzer nicht gefunden")
    if status not in (STATUS_ACTIVE, STATUS_DISABLED):
        raise HTTPException(400, "Ungültiger Status")
    if target.id == user.id and status == STATUS_DISABLED:
        return redirect("/admin/users", "Das eigene Konto kann nicht deaktiviert werden.", "error")
    target.status = status
    if status == STATUS_DISABLED:
        delete_user_sessions(db, target.id)
    db.add(target)
    return redirect("/admin/users", f"Status von {target.username} geändert.", "success")


@router.post("/users/{user_id}/role")
def set_role(
    user_id: int,
    role: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Benutzer nicht gefunden")
    if role not in ROLES:
        raise HTTPException(400, "Ungültige Rolle")
    if target.id == user.id and role != "admin":
        return redirect(
            "/admin/users", "Die eigene Administratorrolle kann nicht entfernt werden.", "error"
        )
    target.role = role
    db.add(target)
    return redirect("/admin/users", f"Rolle von {target.username} ist jetzt {role}.", "success")


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Benutzer nicht gefunden")
    new_password = secrets.token_urlsafe(9)
    target.password_hash = hash_password(new_password)
    delete_user_sessions(db, target.id)
    db.add(target)
    return redirect(
        "/admin/users",
        f"Neues Passwort für {target.username}: {new_password} (jetzt notieren).",
        "success",
    )


@router.post("/users/{user_id}/delete")
def delete_user(user_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Benutzer nicht gefunden")
    if target.id == user.id:
        return redirect("/admin/users", "Das eigene Konto kann nicht gelöscht werden.", "error")
    db.delete(target)
    return redirect("/admin/users", f"{target.username} gelöscht.", "success")


# -------------------------------------------------------------------- settings


@router.get("/settings")
def settings_page(
    request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    return render(
        request, "admin/settings.html", {"registration_mode": get_setting(db, SETTING_REGISTRATION)}
    )


@router.post("/settings")
def save_settings(
    registration_mode: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if registration_mode not in ("open", "approval"):
        raise HTTPException(400, "Ungültiger Wert")
    set_setting(db, SETTING_REGISTRATION, registration_mode)
    return redirect("/admin/settings", "Einstellungen gespeichert.", "success")


# ---------------------------------------------------------------------- import


def _batch_listing(user: User):
    stmt = select(ImportBatch).order_by(ImportBatch.imported_at.desc())
    if not user.is_admin:
        stmt = stmt.where(ImportBatch.imported_by == user.id)
    return stmt


@router.get("/import")
def import_form(
    request: Request, user: User = Depends(require_supervisor), db: Session = Depends(get_db)
):
    batches = list(db.execute(_batch_listing(user).limit(50)).scalars())
    return render(request, "admin/import.html", {"batches": batches, "modules": all_modules(db)})


@router.post("/import")
async def import_upload(
    request: Request,
    file: UploadFile = File(...),
    source: str = Form(""),
    source_url: str = Form(""),
    exam_code: str = Form(""),
    exam_version: str = Form(""),
    rights: str = Form("unknown"),
    user: User = Depends(require_supervisor),
    db: Session = Depends(get_db),
):
    """Import a question or lab file. Imported questions stay unreleased until released."""
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        return redirect("/admin/import", "Die Datei ist größer als 5 MB.", "error")
    filename = (file.filename or "upload.json")[:255]
    try:
        data = parse_json_bytes(raw, filename)
        if data.get("kind") in ("objectives", "terms") and not user.is_admin:
            raise ContentError(
                ["Nur Administratoren dürfen Prüfungsziele oder Glossare importieren."]
            )
        if rights not in ("cleared", "unknown", "unverified"):
            raise ContentError(["Ungültiger Rechtestatus."])
        if data.get("kind") == "questions":
            # form values complete or override the file header
            if source.strip():
                data["source"] = source.strip()
            if exam_version.strip():
                data["exam_version"] = exam_version.strip()
            if exam_code.strip():
                data["exam_code"] = exam_code.strip()
            if source_url.strip():
                data["source_url"] = source_url.strip()
            if rights != "unknown":
                data["rights"] = rights
        result = import_document(db, data, filename=filename, imported_by=user.id)
    except ContentError as exc:
        db.rollback()
        batches = list(db.execute(_batch_listing(user).limit(50)).scalars())
        return render(
            request,
            "admin/import.html",
            {
                "batches": batches,
                "modules": all_modules(db),
                "errors": exc.errors,
                "filename": filename,
            },
            status_code=400,
        )
    msg = f"{filename}: {result.created} neu, {result.updated} aktualisiert ({result.kind})."
    if result.kind == "questions":
        msg += " Die Fragen sind noch nicht freigegeben (Verwaltung › Freigaben)."
    if result.warnings:
        shown = "; ".join(result.warnings[:3])
        more = f" (+{len(result.warnings) - 3} weitere)" if len(result.warnings) > 3 else ""
        msg += f" Mögliche Dubletten: {shown}{more}."
    return redirect("/admin/import", msg, "success")


@router.post("/batches/{batch_id}/delete")
def delete_batch(
    batch_id: int, user: User = Depends(require_supervisor), db: Session = Depends(get_db)
):
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise HTTPException(404, "Import nicht gefunden")
    if not user.is_admin and batch.imported_by != user.id:
        raise HTTPException(403, "Keine Berechtigung")
    if batch.kind == "questions":
        for q in db.execute(select(Question).where(Question.import_batch_id == batch.id)).scalars():
            db.delete(q)
    elif batch.kind == "labs":
        for lab in db.execute(select(Lab).where(Lab.import_batch_id == batch.id)).scalars():
            db.delete(lab)
    db.delete(batch)
    return redirect("/admin/import", f"Import {batch.filename} entfernt.", "success")


# ------------------------------------------------------------------- questions


@router.get("/questions")
def questions(
    request: Request,
    module: str = "",
    batch: int | None = None,
    q: str = "",
    user: User = Depends(require_supervisor),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Question)
        .options(
            selectinload(Question.module),
            selectinload(Question.objective),
            selectinload(Question.batch),
        )
        .order_by(Question.external_id)
    )
    if not user.is_admin:
        stmt = stmt.where((Question.visibility == "public") | (Question.created_by == user.id))
    if module:
        stmt = stmt.join(Module).where(Module.code == module)
    if batch:
        stmt = stmt.where(Question.import_batch_id == batch)
    if q.strip():
        stmt = stmt.where(
            Question.text_en.contains(q.strip()) | Question.external_id.contains(q.strip())
        )
    rows = list(db.execute(stmt.limit(300)).scalars())
    return render(
        request,
        "admin/questions.html",
        {"questions": rows, "modules": all_modules(db), "module": module, "q": q, "batch": batch},
    )


@router.post("/questions/{question_id}/toggle")
def toggle_question(
    question_id: int, user: User = Depends(require_supervisor), db: Session = Depends(get_db)
):
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(404, "Frage nicht gefunden")
    if not user.is_admin and question.created_by != user.id:
        raise HTTPException(403, "Keine Berechtigung")
    question.is_active = not question.is_active
    db.add(question)
    state = "aktiviert" if question.is_active else "deaktiviert"
    return redirect(
        f"/admin/questions?module={question.module.code}",
        f"Frage {question.external_id} {state}.",
        "success",
    )


# ---------------------------------------------------------------------- groups


def _group_for(db: Session, user: User, group_id: int) -> Group:
    group = db.execute(
        select(Group)
        .options(selectinload(Group.members).selectinload(GroupMember.user))
        .where(Group.id == group_id)
    ).scalar_one_or_none()
    if group is None:
        raise HTTPException(404, "Gruppe nicht gefunden")
    if not user.is_admin:
        supervises = any(m.user_id == user.id and m.role == "supervisor" for m in group.members)
        if not supervises:
            raise HTTPException(403, "Keine Berechtigung")
    return group


@router.get("/groups")
def groups(
    request: Request, user: User = Depends(require_supervisor), db: Session = Depends(get_db)
):
    rows = list(
        db.execute(
            select(Group).options(selectinload(Group.members)).order_by(Group.name)
        ).scalars()
    )
    if not user.is_admin:
        rows = [
            g
            for g in rows
            if any(m.user_id == user.id and m.role == "supervisor" for m in g.members)
        ]
    return render(request, "admin/groups.html", {"groups": rows})


@router.post("/groups")
def create_group(
    name: str = Form(...),
    description: str = Form(""),
    join_mode: str = Form("approval"),
    user: User = Depends(require_supervisor),
    db: Session = Depends(get_db),
):
    name = name.strip()[:128]
    if not name:
        return redirect("/admin/groups", "Der Gruppenname darf nicht leer sein.", "error")
    if join_mode not in ("open", "approval"):
        raise HTTPException(400, "Ungültiger Beitrittsmodus")
    if db.execute(select(Group.id).where(Group.name == name)).scalar_one_or_none():
        return redirect("/admin/groups", "Eine Gruppe mit diesem Namen existiert bereits.", "error")
    group = Group(
        name=name, description=description.strip(), join_mode=join_mode, created_by=user.id
    )
    db.add(group)
    db.flush()
    db.add(GroupMember(group_id=group.id, user_id=user.id, role="supervisor", status="active"))
    return redirect(f"/admin/groups/{group.id}", "Gruppe angelegt.", "success")


@router.get("/groups/{group_id}")
def group_detail(
    request: Request,
    group_id: int,
    user: User = Depends(require_supervisor),
    db: Session = Depends(get_db),
):
    group = _group_for(db, user, group_id)
    modules = all_modules(db)
    report = []
    for member in sorted(group.members, key=lambda m: m.user.username):
        if member.status != "active":
            continue
        selected = (
            db.execute(select(UserModule).where(UserModule.user_id == member.user_id))
            .scalars()
            .all()
        )
        selected_ids = {um.module_id for um in selected}
        progress = [module_progress(db, member.user, m) for m in modules if m.id in selected_ids]
        report.append({"member": member, "progress": progress})
    others = list(
        db.execute(
            select(User)
            .where(User.status == STATUS_ACTIVE, User.id.not_in([m.user_id for m in group.members]))
            .order_by(User.username)
        ).scalars()
    )
    return render(request, "admin/group.html", {"group": group, "report": report, "others": others})


@router.post("/groups/{group_id}/members")
def add_member(
    group_id: int,
    user_id: int = Form(...),
    role: str = Form("member"),
    user: User = Depends(require_supervisor),
    db: Session = Depends(get_db),
):
    group = _group_for(db, user, group_id)
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Benutzer nicht gefunden")
    if role not in ("member", "supervisor"):
        raise HTTPException(400, "Ungültige Rolle")
    existing = next((m for m in group.members if m.user_id == user_id), None)
    if existing is None:
        db.add(GroupMember(group_id=group.id, user_id=user_id, role=role, status="active"))
    else:
        existing.role = role
        existing.status = "active"
        db.add(existing)
    return redirect(f"/admin/groups/{group.id}", f"{target.username} ist Mitglied.", "success")


@router.post("/groups/{group_id}/members/{user_id}/approve")
def approve_member(
    group_id: int,
    user_id: int,
    user: User = Depends(require_supervisor),
    db: Session = Depends(get_db),
):
    group = _group_for(db, user, group_id)
    member = next((m for m in group.members if m.user_id == user_id), None)
    if member is None:
        raise HTTPException(404, "Mitglied nicht gefunden")
    member.status = "active"
    db.add(member)
    return redirect(f"/admin/groups/{group.id}", "Mitglied freigegeben.", "success")


@router.post("/groups/{group_id}/members/{user_id}/remove")
def remove_member(
    group_id: int,
    user_id: int,
    user: User = Depends(require_supervisor),
    db: Session = Depends(get_db),
):
    group = _group_for(db, user, group_id)
    member = next((m for m in group.members if m.user_id == user_id), None)
    if member is not None:
        db.delete(member)
    return redirect(f"/admin/groups/{group.id}", "Mitglied entfernt.")


@router.post("/groups/{group_id}/delete")
def delete_group(group_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    if group is not None:
        db.delete(group)
    return redirect("/admin/groups", "Gruppe gelöscht.")


# ----------------------------------------------------------------- releases


def _supervised_groups(db: Session, user: User) -> list[Group]:
    rows = list(
        db.execute(
            select(Group).options(selectinload(Group.members)).order_by(Group.name)
        ).scalars()
    )
    if user.is_admin:
        return rows
    return [
        g for g in rows if any(m.user_id == user.id and m.role == "supervisor" for m in g.members)
    ]


def _releasable_batches(db: Session, user: User) -> list[ImportBatch]:
    """External question pools the user may release: own imports, or all for administrators."""
    stmt = (
        select(ImportBatch)
        .where(ImportBatch.kind == "questions", ImportBatch.supplementary.is_(True))
        .order_by(ImportBatch.module_code, ImportBatch.source, ImportBatch.imported_at)
    )
    if not user.is_admin:
        stmt = stmt.where(ImportBatch.imported_by == user.id)
    return list(db.execute(stmt).scalars())


@router.get("/releases")
def releases(
    request: Request, user: User = Depends(require_supervisor), db: Session = Depends(get_db)
):
    """External question pools and the groups they are released for."""
    batches = _releasable_batches(db, user)
    groups = _supervised_groups(db, user)
    enabled = {
        (gs.group_id, gs.batch_id)
        for gs in db.execute(
            select(GroupSource).where(GroupSource.group_id.in_([g.id for g in groups]))
        ).scalars()
    }
    counts = dict(
        db.execute(
            select(Question.import_batch_id, func.count(Question.id))
            .where(Question.import_batch_id.in_([b.id for b in batches]))
            .group_by(Question.import_batch_id)
        ).all()
    )
    importers = {
        u.id: u.username
        for u in db.execute(
            select(User).where(User.id.in_([b.imported_by for b in batches if b.imported_by]))
        ).scalars()
    }
    return render(
        request,
        "admin/releases.html",
        {
            "batches": batches,
            "groups": groups,
            "enabled": enabled,
            "counts": counts,
            "importers": importers,
        },
    )


@router.post("/releases/group/{group_id}")
async def save_group_releases(
    request: Request,
    group_id: int,
    user: User = Depends(require_supervisor),
    db: Session = Depends(get_db),
):
    """Enable the selected pools for one group. Supervisors may only use their own imports."""
    group = _group_for(db, user, group_id)
    form = await request.form()
    wanted: set[int] = set()
    for raw in form.getlist("batch"):
        try:
            wanted.add(int(raw))
        except ValueError:
            continue
    allowed = {b.id for b in _releasable_batches(db, user)}
    current = {
        gs.batch_id: gs
        for gs in db.execute(select(GroupSource).where(GroupSource.group_id == group.id)).scalars()
    }
    for batch_id in (wanted & allowed) - set(current):
        db.add(GroupSource(group_id=group.id, batch_id=batch_id, enabled_by=user.id))
    for batch_id in (set(current) & allowed) - wanted:
        db.delete(current[batch_id])
    return redirect("/admin/releases", f"Freigaben für {group.name} gespeichert.", "success")


@router.post("/releases/{batch_id}/global")
def release_global(
    batch_id: int,
    released: str = Form("0"),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Release or withdraw a pool system-wide (administrators only)."""
    batch = db.get(ImportBatch, batch_id)
    if batch is None or batch.kind != "questions":
        raise HTTPException(404, "Import nicht gefunden")
    set_batch_release(db, batch, released == "1")
    state = "systemweit freigegeben" if batch.released else "systemweite Freigabe zurückgenommen"
    return redirect("/admin/releases", f"{batch.source}: {state}.", "success")


# ---------------------------------------------------------------- statistics


@router.get("/stats")
def stats(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    attempts = db.execute(select(func.count(Attempt.id))).scalar_one()
    by_module = db.execute(
        select(Module.code, func.count(Question.id))
        .join(Question, Question.module_id == Module.id)
        .group_by(Module.code)
        .order_by(Module.code)
    ).all()
    return render(request, "admin/stats.html", {"attempts": attempts, "by_module": by_module})
