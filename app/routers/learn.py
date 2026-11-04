"""Practice mode: English questions with optional German language help."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import get_current_user, get_db
from app.models import MODE_PRACTICE, Objective, Question, User
from app.services import (
    grade,
    module_by_code,
    pick_practice_question,
    record_attempt,
    terms_for_question,
    user_term_status,
    visible_questions,
)
from app.web import render

router = APIRouter()


def _objective(db: Session, code: str | None) -> Objective | None:
    if not code:
        return None
    obj = db.execute(select(Objective).where(Objective.code == code)).scalar_one_or_none()
    if obj is None:
        raise HTTPException(404, "Prüfungsziel nicht gefunden")
    return obj


def _question_context(db: Session, user: User, question: Question, with_help: bool) -> dict:
    terms = terms_for_question(db, question) if with_help else []
    statuses = user_term_status(db, user, [t.id for t in terms])
    return {
        "question": question,
        "terms": [
            {"id": t.id, "term": t.term, "de": t.translation_de,
             "explanation": t.explanation_de, "status": statuses.get(t.id, "")}
            for t in terms
        ],
    }


@router.get("/learn/{code}")
def practice(request: Request, code: str, objective: str | None = None, skip: int | None = None,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    module = module_by_code(db, code)
    if module is None:
        raise HTTPException(404, "Modul nicht gefunden")
    obj = _objective(db, objective)
    question = pick_practice_question(db, user, module, obj, exclude_id=skip)
    if question is None:
        return render(request, "learn/empty.html", {"module": module, "objective": obj})
    ctx = _question_context(db, user, question, with_help=True)
    ctx.update({"module": module, "objective": obj, "mode": MODE_PRACTICE})
    return render(request, "learn/question.html", ctx)


@router.post("/learn/{code}/answer")
async def answer(request: Request, code: str, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    module = module_by_code(db, code)
    if module is None:
        raise HTTPException(404, "Modul nicht gefunden")
    form = await request.form()
    try:
        question_id = int(form.get("question_id", ""))
    except ValueError as exc:
        raise HTTPException(400, "Ungültige Frage") from exc
    question = db.execute(
        visible_questions(db, user)
        .options(selectinload(Question.choices))
        .where(Question.id == question_id, Question.module_id == module.id)
    ).scalar_one_or_none()
    if question is None:
        raise HTTPException(404, "Frage nicht gefunden")
    selected: set[int] = set()
    for raw in form.getlist("choice"):
        try:
            selected.add(int(raw))
        except ValueError:
            continue
    valid_ids = {c.id for c in question.choices}
    selected &= valid_ids
    used_help = form.get("used_help") == "1"
    is_correct = grade(question, selected)
    record_attempt(db, user, question, is_correct, used_help, MODE_PRACTICE)
    obj_code = form.get("objective") or None
    obj = _objective(db, obj_code) if obj_code else None
    ctx = _question_context(db, user, question, with_help=True)
    ctx.update({"module": module, "objective": obj, "selected": selected,
                "is_correct": is_correct, "used_help": used_help, "mode": MODE_PRACTICE})
    return render(request, "learn/result.html", ctx)


@router.get("/question/{question_id}")
def question_detail(request: Request, question_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Review a single question (used from exam results and progress pages)."""
    question = db.execute(
        visible_questions(db, user).options(selectinload(Question.choices))
        .where(Question.id == question_id)
    ).scalar_one_or_none()
    if question is None:
        raise HTTPException(404, "Frage nicht gefunden")
    ctx = _question_context(db, user, question, with_help=True)
    ctx.update({"module": question.module, "objective": question.objective,
                "selected": question.correct_choice_ids, "is_correct": None,
                "review": True, "mode": "review"})
    return render(request, "learn/result.html", ctx)
