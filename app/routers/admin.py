"""Administration: users, settings, content import, question management and groups."""

from __future__ import annotations

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
    LAB_COMPLETED,
    LAB_STARTED,
    MODE_PRACTICE,
    ROLE_LEARNER,
    ROLES,
    STATUS_ACTIVE,
    STATUS_DISABLED,
    STATUS_PENDING,
    Attempt,
    Exam,
    Group,
    GroupLab,
    GroupMember,
    GroupSource,
    ImportBatch,
    Lab,
    LabProgress,
    Module,
    Objective,
    Question,
    Term,
    Topic,
    User,
    UserModule,
)
from app.routers.auth import USERNAME_RE
from app.security import delete_user_sessions, generate_password, hash_password, password_error
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
    if problem := password_error(password):
        return redirect("/admin/users", problem, "error")
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
    new_password = generate_password()
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
    lab_report = _group_lab_report(db, group)
    return render(
        request,
        "admin/group.html",
        {"group": group, "report": report, "others": others, **lab_report},
    )


def _group_lab_report(db: Session, group: Group) -> dict:
    """Lab status of the group's active members (not started / started / completed) and the
    labs recommended for the group. Only data of the group's own members is read."""
    member_ids = [m.user_id for m in group.members if m.status == STATUS_ACTIVE]
    labs = list(
        db.execute(
            select(Lab)
            .options(selectinload(Lab.objective), selectinload(Lab.module))
            .where(Lab.visibility == "public")
            .order_by(Lab.module_id, Lab.id)
        ).scalars()
    )
    rows = []
    if member_ids:
        rows = db.execute(select(LabProgress).where(LabProgress.user_id.in_(member_ids))).scalars()
    status: dict[int, dict[int, str]] = {}  # lab id -> user id -> status
    for row in rows:
        status.setdefault(row.lab_id, {})[row.user_id] = row.status
    names = {m.user_id: m.user.label for m in group.members}
    recommended = set(
        db.execute(select(GroupLab.lab_id).where(GroupLab.group_id == group.id)).scalars()
    )
    lab_rows = []
    for lab in labs:
        per_user = status.get(lab.id, {})
        completed = sorted(names[u] for u in member_ids if per_user.get(u) == LAB_COMPLETED)
        started = sorted(names[u] for u in member_ids if per_user.get(u) == LAB_STARTED)
        not_started = sorted(names[u] for u in member_ids if u not in per_user)
        lab_rows.append(
            {
                "lab": lab,
                "recommended": lab.id in recommended,
                "completed": completed,
                "started": started,
                "not_started": not_started,
            }
        )
    member_labs = {
        u: {
            "completed": sum(1 for s in status.values() if s.get(u) == LAB_COMPLETED),
            "started": sum(1 for s in status.values() if s.get(u) == LAB_STARTED),
        }
        for u in member_ids
    }
    return {"lab_rows": lab_rows, "member_labs": member_labs, "lab_total": len(labs)}


@router.get("/groups/{group_id}/auswertung")
def group_evaluation(
    request: Request,
    group_id: int,
    user: User = Depends(require_supervisor),
    db: Session = Depends(get_db),
):
    """Where does the group stand per exam objective? Aggregates the members' practice,
    exam and entry-test attempts (no grading, no per-member ranking)."""
    group = _group_for(db, user, group_id)
    member_ids = [m.user_id for m in group.members if m.status == STATUS_ACTIVE]
    report = _objective_report(db, member_ids)
    return render(request, "admin/group_eval.html", {"group": group, **report})


MIN_ATTEMPTS_FOR_VERDICT = 5
LOW_CORRECT_PERCENT = 60
HIGH_HELP_PERCENT = 50


def _objective_report(db: Session, member_ids: list[int]) -> dict:
    rows = []
    if member_ids:
        rows = db.execute(
            select(
                Module.code,
                Topic.code,
                Topic.title,
                Objective.code,
                Objective.title,
                Attempt.question_id,
                Attempt.user_id,
                Attempt.is_correct,
                Attempt.used_help,
                Attempt.mode,
            )
            .join(Question, Question.id == Attempt.question_id)
            .join(Module, Module.id == Question.module_id)
            .outerjoin(Objective, Objective.id == Question.objective_id)
            .outerjoin(Topic, Topic.id == Objective.topic_id)
            .where(Attempt.user_id.in_(member_ids))
        ).all()
    objectives: dict[tuple, dict] = {}
    questions: dict[int, dict] = {}
    for mod, tcode, ttitle, ocode, otitle, qid, uid, ok, help_used, mode in rows:
        key = (mod, tcode or "", ocode or "")
        entry = objectives.setdefault(
            key,
            {
                "module": mod,
                "topic": tcode or "",
                "topic_title": ttitle or "",
                "objective": ocode or "ohne Ziel",
                "title": otitle or "",
                "attempts": 0,
                "correct": 0,
                "help": 0,
                "practice": 0,
                "members": set(),
            },
        )
        entry["attempts"] += 1
        entry["correct"] += int(ok)
        entry["members"].add(uid)
        if mode == MODE_PRACTICE:
            entry["practice"] += 1
            entry["help"] += int(help_used)
        q = questions.setdefault(qid, {"attempts": 0, "wrong": 0, "objective": ocode or ""})
        q["attempts"] += 1
        q["wrong"] += int(not ok)
    result = []
    for entry in sorted(objectives.values(), key=lambda e: (e["module"], e["objective"])):
        entry["members"] = len(entry["members"])
        entry["percent"] = round(100 * entry["correct"] / entry["attempts"])
        entry["help_percent"] = (
            round(100 * entry["help"] / entry["practice"]) if entry["practice"] else 0
        )
        entry["verdict"] = ""
        if entry["attempts"] >= MIN_ATTEMPTS_FOR_VERDICT:
            if entry["percent"] < LOW_CORRECT_PERCENT:
                entry["verdict"] = "vertiefen"
            elif entry["help_percent"] >= HIGH_HELP_PERCENT:
                entry["verdict"] = "Fachenglisch üben"
            else:
                entry["verdict"] = "sicher"
        result.append(entry)
    # questions that are wrong unusually often (at least two wrong answers, half or more)
    frequent = [
        (qid, q)
        for qid, q in questions.items()
        if q["wrong"] >= 2 and q["wrong"] * 2 >= q["attempts"]
    ]
    frequent.sort(key=lambda item: (-item[1]["wrong"], item[0]))
    frequent_questions = []
    if frequent:
        qmap = {
            q.id: q
            for q in db.execute(
                select(Question)
                .options(selectinload(Question.objective))
                .where(Question.id.in_([qid for qid, _ in frequent[:10]]))
            ).scalars()
        }
        for qid, q in frequent[:10]:
            question = qmap.get(qid)
            if question is not None:
                frequent_questions.append({"question": question, **q})
    modules = sorted({e["module"] for e in result})
    return {
        "objectives": result,
        "frequent_questions": frequent_questions,
        "modules": modules,
        "member_count": len(member_ids),
        "min_attempts": MIN_ATTEMPTS_FOR_VERDICT,
        "low_percent": LOW_CORRECT_PERCENT,
        "high_help": HIGH_HELP_PERCENT,
    }


@router.post("/groups/{group_id}/labs")
async def set_group_labs(
    request: Request,
    group_id: int,
    user: User = Depends(require_supervisor),
    db: Session = Depends(get_db),
):
    """Replace the set of labs recommended to the group (checkbox form)."""
    group = _group_for(db, user, group_id)
    form = await request.form()
    wanted = {int(v) for v in form.getlist("lab_ids") if str(v).isdigit()}
    valid = set(db.execute(select(Lab.id).where(Lab.visibility == "public")).scalars())
    wanted &= valid
    existing = {
        gl.lab_id: gl
        for gl in db.execute(select(GroupLab).where(GroupLab.group_id == group.id)).scalars()
    }
    for lab_id, gl in existing.items():
        if lab_id not in wanted:
            db.delete(gl)
    for lab_id in wanted - set(existing):
        db.add(GroupLab(group_id=group.id, lab_id=lab_id))
    return redirect(f"/admin/groups/{group.id}", f"{len(wanted)} LABs für die Gruppe empfohlen.")


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
    """Supplementary question pools the user may release for groups.

    Administrators: all. Supervisors: their own imports and the pools bundled with the
    trainer (content/questions/extra), so that a lecturer can run a group without asking the
    administrator; the rights note of each pool is shown next to it."""
    stmt = (
        select(ImportBatch)
        .where(ImportBatch.kind == "questions", ImportBatch.supplementary.is_(True))
        .order_by(ImportBatch.module_code, ImportBatch.source, ImportBatch.imported_at)
    )
    if not user.is_admin:
        stmt = stmt.where(or_(ImportBatch.imported_by == user.id, ImportBatch.bundled.is_(True)))
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
    """Enable the selected pools for one group (own imports and bundled pools for supervisors)."""
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
