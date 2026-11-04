"""Dashboard, module selection, module overview, progress, groups and PWA files."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import PACKAGE_DIR
from app.deps import get_current_user, get_db, get_optional_user
from app.models import Group, GroupMember, Lab, Question, User, UserModule, UserTerm
from app.services import (
    all_modules,
    module_by_code,
    module_progress,
    user_module,
    user_modules,
    visible_questions,
)
from app.web import redirect, render

router = APIRouter()


@router.get("/")
def index(request: Request, user: User | None = Depends(get_optional_user),
          db: Session = Depends(get_db)):
    if user is None:
        return render(request, "landing.html", {"modules": all_modules(db)})
    selected = user_modules(db, user)
    if not selected:
        return redirect("/modules")
    progress = [module_progress(db, user, um.module) for um in selected]
    learning_terms = db.execute(
        select(func.count(UserTerm.id)).where(UserTerm.user_id == user.id,
                                              UserTerm.status == "learning")
    ).scalar_one()
    return render(request, "dashboard.html",
                  {"progress": progress, "learning_terms": learning_terms,
                   "selected": {um.module_id: um for um in selected}})


@router.get("/modules")
def modules(request: Request, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    mods = all_modules(db)
    selected = {um.module_id for um in user_modules(db, user)}
    counts: dict[int, int] = {}
    for m in mods:
        counts[m.id] = db.execute(
            select(func.count()).select_from(
                visible_questions(db, user).where(Question.module_id == m.id).subquery()
            )
        ).scalar_one()
    labs = dict(db.execute(select(Lab.module_id, func.count(Lab.id)).group_by(Lab.module_id)).all())
    return render(request, "modules.html",
                  {"modules": mods, "selected": selected, "counts": counts, "labs": labs})


@router.post("/modules/select")
def select_module(request: Request, module_code: str = Form(...), action: str = Form("add"),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    module = module_by_code(db, module_code)
    if module is None:
        raise HTTPException(404, "Modul nicht gefunden")
    existing = user_module(db, user, module)
    if action == "remove" and existing:
        db.delete(existing)
        return redirect("/modules", f"Modul {module.code} abgewählt.")
    if action == "add" and existing is None:
        db.add(UserModule(user_id=user.id, module_id=module.id))
        return redirect(f"/module/{module.code}", f"Modul {module.code} hinzugefügt.", "success")
    return redirect("/modules")


@router.get("/module/{code}")
def module_overview(request: Request, code: str, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    module = module_by_code(db, code)
    if module is None:
        raise HTTPException(404, "Modul nicht gefunden")
    um = user_module(db, user, module)
    progress = module_progress(db, user, module)
    labs = list(db.execute(select(Lab).where(Lab.module_id == module.id).order_by(Lab.id)).scalars())
    return render(request, "module.html",
                  {"module": module, "progress": progress, "um": um, "labs": labs})


@router.get("/progress")
def progress_page(request: Request, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    selected = user_modules(db, user)
    progress = [module_progress(db, user, um.module) for um in selected]
    terms = list(
        db.execute(select(UserTerm).where(UserTerm.user_id == user.id)).scalars()
    )
    return render(request, "progress.html",
                  {"progress": progress, "terms_learning": sum(t.status == "learning" for t in terms),
                   "terms_known": sum(t.status == "known" for t in terms)})


# ---------------------------------------------------------------------- groups


@router.get("/groups")
def groups(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    all_groups = list(db.execute(select(Group).order_by(Group.name)).scalars())
    memberships = {
        m.group_id: m for m in db.execute(
            select(GroupMember).where(GroupMember.user_id == user.id)
        ).scalars()
    }
    return render(request, "groups.html", {"groups": all_groups, "memberships": memberships})


@router.post("/groups/{group_id}/join")
def join_group(group_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(404, "Gruppe nicht gefunden")
    existing = db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user.id)
    ).scalar_one_or_none()
    if existing:
        return redirect("/groups")
    status = "active" if group.join_mode == "open" else "pending"
    db.add(GroupMember(group_id=group_id, user_id=user.id, status=status))
    msg = "Du bist der Gruppe beigetreten." if status == "active" else "Beitrittsanfrage gesendet."
    return redirect("/groups", msg, "success")


@router.post("/groups/{group_id}/leave")
def leave_group(group_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user.id)
    ).scalar_one_or_none()
    if existing:
        db.delete(existing)
    return redirect("/groups", "Du hast die Gruppe verlassen.")


# ------------------------------------------------------------------------ PWA


@router.get("/offline", include_in_schema=False)
def offline(request: Request, user: User | None = Depends(get_optional_user)):
    return render(request, "offline.html", {})


@router.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(PACKAGE_DIR / "static" / "manifest.webmanifest",
                        media_type="application/manifest+json")


@router.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(PACKAGE_DIR / "static" / "sw.js", media_type="application/javascript",
                        headers={"Cache-Control": "no-cache"})
