"""Lab instructions with self-check questions. Nothing is executed by the app."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import get_current_user, get_db
from app.models import Lab, LabProgress, User
from app.services import all_modules, user_modules, visible_labs
from app.web import redirect, render

router = APIRouter()


def _progress_map(db: Session, user: User) -> dict[int, LabProgress]:
    rows = db.execute(select(LabProgress).where(LabProgress.user_id == user.id)).scalars()
    return {r.lab_id: r for r in rows}


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
    done = _progress_map(db, user)
    return render(
        request,
        "labs/list.html",
        {"modules": modules, "labs": rows, "selected": selected, "done": done},
    )


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
    return render(request, "labs/detail.html", {"lab": lab, "progress": progress})


@router.post("/lab/{lab_id}/complete")
def lab_complete(
    lab_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    lab = db.execute(visible_labs(db, user).where(Lab.id == lab_id)).scalar_one_or_none()
    if lab is None:
        raise HTTPException(404, "Lab nicht gefunden")
    existing = _progress_map(db, user).get(lab.id)
    if existing is None:
        db.add(LabProgress(user_id=user.id, lab_id=lab.id))
    return redirect(f"/lab/{lab.id}", "Lab als erledigt markiert.", "success")


@router.post("/lab/{lab_id}/reset")
def lab_reset(lab_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = _progress_map(db, user).get(lab_id)
    if existing is not None:
        db.delete(existing)
    return redirect(f"/lab/{lab_id}", "Markierung entfernt.")
