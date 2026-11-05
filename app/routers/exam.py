"""Exam simulation (no language help, timer) and entry tests."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.deps import get_current_user, get_db
from app.models import MODE_ENTRY, MODE_EXAM, Exam, Question, Topic, User, utcnow
from app.services import (
    answer_feedback,
    grade_submission,
    module_by_code,
    record_attempt,
    select_exam_questions,
    stored_answer_correct,
    user_module,
)
from app.web import redirect, render

router = APIRouter()


def _load_exam(db: Session, user: User, exam_id: int) -> Exam:
    exam = db.get(Exam, exam_id)
    if exam is None or exam.user_id != user.id:
        raise HTTPException(404, "Prüfung nicht gefunden")
    return exam


def _questions(db: Session, exam: Exam) -> list[Question]:
    if not exam.question_ids:
        return []
    rows = db.execute(
        select(Question)
        .options(selectinload(Question.choices))
        .where(Question.id.in_(exam.question_ids))
    ).scalars()
    by_id = {q.id: q for q in rows}
    return [by_id[i] for i in exam.question_ids if i in by_id]


@router.get("/exam/{code}/start")
def start_exam(
    code: str,
    topic: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    module = module_by_code(db, code)
    if module is None:
        raise HTTPException(404, "Modul nicht gefunden")
    topic_obj = None
    count = settings.exam_question_count
    minutes = settings.exam_minutes
    if topic:
        topic_obj = db.execute(select(Topic).where(Topic.code == topic)).scalar_one_or_none()
        if topic_obj is None or topic_obj.module_id != module.id:
            raise HTTPException(404, "Thema nicht gefunden")
        count = settings.topic_exam_question_count
        minutes = max(10, round(settings.exam_minutes * count / settings.exam_question_count))
    ids = select_exam_questions(db, user, module, count, topic_obj)
    if not ids:
        return redirect(
            f"/module/{module.code}", "Für diese Auswahl gibt es noch keine Fragen.", "error"
        )
    exam = Exam(
        user_id=user.id,
        module_id=module.id,
        topic_id=topic_obj.id if topic_obj else None,
        mode=MODE_EXAM,
        question_ids=ids,
        duration_minutes=minutes,
        total_count=len(ids),
    )
    db.add(exam)
    db.flush()
    return redirect(f"/exam/{exam.id}")


@router.get("/entry/{code}/start")
def start_entry(code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = get_settings()
    module = module_by_code(db, code)
    if module is None:
        raise HTTPException(404, "Modul nicht gefunden")
    ids = select_exam_questions(db, user, module, settings.entry_test_question_count)
    if not ids:
        return redirect(
            f"/module/{module.code}", "Für dieses Modul gibt es noch keine Fragen.", "error"
        )
    exam = Exam(
        user_id=user.id,
        module_id=module.id,
        mode=MODE_ENTRY,
        question_ids=ids,
        duration_minutes=0,
        total_count=len(ids),
    )
    db.add(exam)
    db.flush()
    return redirect(f"/exam/{exam.id}")


@router.get("/exam/{exam_id:int}")
def exam_page(
    request: Request,
    exam_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exam = _load_exam(db, user, exam_id)
    if exam.finished_at:
        return redirect(f"/exam/{exam.id}/result")
    questions = _questions(db, exam)
    deadline = None
    remaining = None
    if exam.duration_minutes:
        deadline = exam.started_at + timedelta(minutes=exam.duration_minutes)
        remaining = max(0, int((deadline - utcnow()).total_seconds()))
    return render(
        request,
        "exam/exam.html",
        {"exam": exam, "questions": questions, "remaining_seconds": remaining},
    )


@router.post("/exam/{exam_id:int}/submit")
async def submit_exam(
    request: Request,
    exam_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exam = _load_exam(db, user, exam_id)
    if exam.finished_at:
        return redirect(f"/exam/{exam.id}/result")
    form = await request.form()
    questions = _questions(db, exam)
    answers: dict[str, list[int]] = {}
    correct = 0
    for q in questions:
        if q.kind == "text":
            raw_values = [str(form.get(f"q{q.id}_text", ""))]
        else:
            raw_values = [str(v) for v in form.getlist(f"q{q.id}")]
        ok, stored = grade_submission(q, raw_values)
        correct += int(ok)
        answers[str(q.id)] = stored
        record_attempt(db, user, q, ok, used_help=False, mode=exam.mode, exam_id=exam.id)
    exam.answers = answers
    exam.correct_count = correct
    exam.total_count = len(questions)
    exam.finished_at = utcnow()
    if exam.mode == MODE_ENTRY:
        um = user_module(db, user, exam.module)
        if um is not None:
            um.entry_done = True
            um.entry_result = _topic_scores(exam, questions)
            db.add(um)
    db.add(exam)
    return redirect(f"/exam/{exam.id}/result")


def _topic_scores(exam: Exam, questions: list[Question]) -> dict:
    per_topic: dict[str, dict] = defaultdict(lambda: {"correct": 0, "total": 0, "title": ""})
    for q in questions:
        topic = q.objective.topic if q.objective else None
        code = topic.code if topic else "other"
        entry = per_topic[code]
        entry["title"] = topic.title if topic else "Sonstige"
        entry["total"] += 1
        entry["correct"] += int(stored_answer_correct(q, exam.answers.get(str(q.id), [])))
    return {"percent": exam.percent, "topics": dict(per_topic)}


@router.get("/exam/{exam_id:int}/result")
def exam_result(
    request: Request,
    exam_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exam = _load_exam(db, user, exam_id)
    if not exam.finished_at:
        return redirect(f"/exam/{exam.id}")
    questions = _questions(db, exam)
    details = []
    for q in questions:
        stored = exam.answers.get(str(q.id), [])
        selected = stored if q.kind == "text" else set(stored)
        details.append(
            {
                "question": q,
                "selected": selected,
                "correct": stored_answer_correct(q, stored),
                "feedback": answer_feedback(q, selected) if q.kind != "text" else None,
            }
        )
    scores = _topic_scores(exam, questions)
    return render(
        request,
        "exam/result.html",
        {"exam": exam, "details": details, "topic_scores": scores["topics"]},
    )


@router.get("/exams")
def exam_history(
    request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    exams = list(
        db.execute(
            select(Exam)
            .options(selectinload(Exam.module), selectinload(Exam.topic))
            .where(Exam.user_id == user.id)
            .order_by(Exam.started_at.desc())
        ).scalars()
    )
    return render(request, "exam/history.html", {"exams": exams})
