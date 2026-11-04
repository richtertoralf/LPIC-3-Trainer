"""Technical vocabulary: personal term list, glossary and flashcard review."""

from __future__ import annotations

import random

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import get_current_user, get_db
from app.models import Term, User, UserTerm, utcnow
from app.web import redirect, render

router = APIRouter()


def _user_terms(db: Session, user: User) -> list[UserTerm]:
    return list(
        db.execute(
            select(UserTerm)
            .options(selectinload(UserTerm.term))
            .where(UserTerm.user_id == user.id)
            .order_by(UserTerm.updated_at.desc())
        ).scalars()
    )


@router.get("/vocab")
def vocab(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = _user_terms(db, user)
    return render(
        request,
        "vocab/list.html",
        {
            "learning": [r for r in rows if r.status == "learning"],
            "known": [r for r in rows if r.status == "known"],
        },
    )


@router.get("/vocab/review")
def review(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = [r for r in _user_terms(db, user) if r.status == "learning"]
    if not rows:
        return redirect("/vocab", "Keine Begriffe zum Wiederholen. Markiere Begriffe beim Üben.")
    rows.sort(key=lambda r: (r.reviews, random.random()))
    return render(request, "vocab/review.html", {"item": rows[0], "remaining": len(rows)})


@router.post("/vocab/{term_id}/status")
def set_status(
    term_id: int,
    status: str = Form(...),
    next: str = Form("/vocab"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if status not in ("learning", "known", "remove"):
        raise HTTPException(400, "Ungültiger Status")
    term = db.get(Term, term_id)
    if term is None:
        raise HTTPException(404, "Begriff nicht gefunden")
    row = db.execute(
        select(UserTerm).where(UserTerm.user_id == user.id, UserTerm.term_id == term_id)
    ).scalar_one_or_none()
    if status == "remove":
        if row:
            db.delete(row)
    else:
        if row is None:
            row = UserTerm(user_id=user.id, term_id=term_id)
        row.status = status
        row.reviews += 1
        row.updated_at = utcnow()
        db.add(row)
    if not next.startswith("/") or next.startswith("//"):
        next = "/vocab"
    return redirect(next)


@router.get("/glossary")
def glossary(
    request: Request,
    q: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Term).order_by(Term.term)
    needle = q.strip().lower()
    if needle:
        stmt = stmt.where(Term.term.contains(needle) | Term.translation_de.contains(needle))
    terms = list(db.execute(stmt).scalars())
    mine = {
        r.term_id: r.status
        for r in db.execute(select(UserTerm).where(UserTerm.user_id == user.id)).scalars()
    }
    return render(request, "vocab/glossary.html", {"terms": terms, "q": q, "mine": mine})
