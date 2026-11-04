"""JSON endpoints for dynamic parts of the UI."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Question, Term, User, UserTerm, utcnow
from app.services import module_progress, terms_for_question, user_modules, visible_questions

router = APIRouter(prefix="/api")


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "role": user.role}


@router.get("/progress")
def progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = []
    for um in user_modules(db, user):
        p = module_progress(db, user, um.module)
        result.append(
            {
                "module": um.module.code,
                "title": um.module.title,
                "questions": p.total,
                "answered": p.answered,
                "correct": p.correct,
                "percent_correct": p.percent_correct,
                "help_rate": p.help_rate,
                "labs_done": p.labs_done,
                "labs_total": p.labs_total,
                "best_exam": p.best_exam.percent if p.best_exam else None,
            }
        )
    return {"modules": result}


@router.get("/questions/{question_id}/terms")
def question_terms(
    question_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    question = db.execute(
        visible_questions(db, user).where(Question.id == question_id)
    ).scalar_one_or_none()
    if question is None:
        raise HTTPException(404, "Frage nicht gefunden")
    return {
        "terms": [
            {"id": t.id, "term": t.term, "de": t.translation_de, "explanation": t.explanation_de}
            for t in terms_for_question(db, question)
        ]
    }


@router.post("/terms/{term_id}/learn")
def learn_term(term_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    term = db.get(Term, term_id)
    if term is None:
        raise HTTPException(404, "Begriff nicht gefunden")
    row = db.execute(
        select(UserTerm).where(UserTerm.user_id == user.id, UserTerm.term_id == term_id)
    ).scalar_one_or_none()
    if row is None:
        row = UserTerm(user_id=user.id, term_id=term_id, status="learning")
    else:
        row.status = "learning"
        row.updated_at = utcnow()
    db.add(row)
    db.flush()
    return {"ok": True, "term": term.term, "status": row.status}
