"""Lab tasks with hints, success criteria and self-checks. Nothing is executed by the app.

Learners manage their own lab status (not started / started / completed). Supervisors see
additional instructor notes. The lab environment guide (docs/lab-umgebung.md) is rendered
as a page of its own learning area.
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import PROJECT_DIR
from app.deps import get_current_user, get_db
from app.markdown import render_markdown
from app.models import (
    LAB_COMPLETED,
    LAB_STARTED,
    STATUS_ACTIVE,
    Group,
    GroupLab,
    GroupMember,
    Lab,
    LabProgress,
    User,
    utcnow,
)
from app.services import all_modules, user_modules, visible_labs
from app.web import redirect, render

router = APIRouter()

ENVIRONMENT_GUIDE = PROJECT_DIR / "docs" / "lab-umgebung.md"


def _progress_map(db: Session, user: User) -> dict[int, LabProgress]:
    rows = db.execute(select(LabProgress).where(LabProgress.user_id == user.id)).scalars()
    return {r.lab_id: r for r in rows}


def _recommendations(db: Session, user: User) -> dict[int, list[str]]:
    """lab id -> names of the user's groups that recommend the lab."""
    rows = db.execute(
        select(GroupLab.lab_id, Group.name)
        .join(Group, Group.id == GroupLab.group_id)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user.id, GroupMember.status == STATUS_ACTIVE)
        .order_by(Group.name)
    ).all()
    result: dict[int, list[str]] = defaultdict(list)
    for lab_id, name in rows:
        result[lab_id].append(name)
    return result


@router.get("/labs")
def labs(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    selected = {um.module_id for um in user_modules(db, user)}
    modules = all_modules(db)
    rows = list(
        db.execute(
            visible_labs(db, user)
            .options(selectinload(Lab.objective))
            .order_by(Lab.module_id, Lab.id)
        ).scalars()
    )
    progress = _progress_map(db, user)
    return render(
        request,
        "labs/list.html",
        {
            "modules": modules,
            "labs": rows,
            "selected": selected,
            "progress": progress,
            "recommended": _recommendations(db, user),
        },
    )


@router.get("/labs/umgebung")
def lab_environment(request: Request, user: User = Depends(get_current_user)):
    """The learner's own lab environment: a learning area of its own, rendered from docs/."""
    if not ENVIRONMENT_GUIDE.is_file():
        raise HTTPException(404, "Anleitung nicht gefunden")
    body = render_markdown(ENVIRONMENT_GUIDE.read_text(encoding="utf-8"))
    return render(request, "labs/environment.html", {"body": body})


@router.get("/lab/{lab_id}")
def lab_detail(
    request: Request,
    lab_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lab = db.execute(
        visible_labs(db, user)
        .options(selectinload(Lab.objective), selectinload(Lab.module))
        .where(Lab.id == lab_id)
    ).scalar_one_or_none()
    if lab is None:
        raise HTTPException(404, "Lab nicht gefunden")
    progress = _progress_map(db, user).get(lab.id)
    practice_url = None
    if lab.objective is not None:
        practice_url = f"/learn/{lab.module.code}?objective={lab.objective.code}"
    return render(
        request,
        "labs/detail.html",
        {
            "lab": lab,
            "progress": progress,
            "practice_url": practice_url,
            "recommended_by": _recommendations(db, user).get(lab.id, []),
            # instructor notes are shown to supervisors and administrators only
            "instructor": user.is_supervisor,
        },
    )


def _visible_lab(db: Session, user: User, lab_id: int) -> Lab:
    lab = db.execute(visible_labs(db, user).where(Lab.id == lab_id)).scalar_one_or_none()
    if lab is None:
        raise HTTPException(404, "Lab nicht gefunden")
    return lab


@router.post("/lab/{lab_id}/start")
def lab_start(lab_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lab = _visible_lab(db, user, lab_id)
    existing = _progress_map(db, user).get(lab.id)
    if existing is None:
        db.add(LabProgress(user_id=user.id, lab_id=lab.id, status=LAB_STARTED))
    else:
        existing.status = LAB_STARTED
        existing.started_at = existing.started_at or utcnow()
        existing.completed_at = None
    return redirect(f"/lab/{lab.id}", "Lab als „in Bearbeitung“ markiert.", "success")


@router.post("/lab/{lab_id}/complete")
def lab_complete(
    lab_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    lab = _visible_lab(db, user, lab_id)
    existing = _progress_map(db, user).get(lab.id)
    now = utcnow()
    if existing is None:
        db.add(LabProgress(user_id=user.id, lab_id=lab.id, status=LAB_COMPLETED, completed_at=now))
    else:
        existing.status = LAB_COMPLETED
        existing.completed_at = now
    return redirect(f"/lab/{lab.id}", "Lab als abgeschlossen markiert.", "success")


@router.post("/lab/{lab_id}/reset")
def lab_reset(lab_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = _progress_map(db, user).get(lab_id)
    if existing is not None:
        db.delete(existing)
    return redirect(f"/lab/{lab_id}", "Markierung entfernt.")
