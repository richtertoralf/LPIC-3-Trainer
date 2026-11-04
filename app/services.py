"""Learning logic shared by routers: visibility, progress and question selection."""

from __future__ import annotations

import random
import re
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    MODE_PRACTICE,
    Attempt,
    Exam,
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
    UserTerm,
)

# ------------------------------------------------------------------- visibility


def enabled_batch_ids(db: Session, user: User) -> list[int]:
    """Supplementary import batches enabled for a group the user is an active member of."""
    my_groups = select(GroupMember.group_id).where(
        GroupMember.user_id == user.id, GroupMember.status == "active"
    )
    rows = db.execute(select(GroupSource.batch_id).where(GroupSource.group_id.in_(my_groups)))
    return list({r for r in rows.scalars()})


def visible_questions(db: Session, user: User):
    """Select statement for active questions the user may see.

    Learners see the released pool (bundled project questions and imports released
    system-wide by an administrator) plus imports a supervisor enabled for one of their
    groups. Administrators see everything, importers see their own imports.
    """
    stmt = select(Question).where(Question.is_active.is_(True))
    if user.is_admin:
        return stmt
    enabled = enabled_batch_ids(db, user)
    return stmt.where(
        or_(
            Question.visibility == "public",
            Question.created_by == user.id,
            Question.import_batch_id.in_(enabled),
        )
    )


def set_batch_release(db: Session, batch: ImportBatch, released: bool) -> None:
    """Release or withdraw an import batch system-wide (administrators only)."""
    batch.released = released
    batch.visibility = "public" if released else "private"
    db.add(batch)
    db.execute(
        Question.__table__.update()
        .where(Question.import_batch_id == batch.id)
        .values(visibility=batch.visibility)
    )
    db.flush()


def enabled_sources(db: Session, user: User, module: Module) -> list[ImportBatch]:
    """External (supplementary) batches of a module the user may currently practise."""
    stmt = select(ImportBatch).where(
        ImportBatch.supplementary.is_(True), ImportBatch.module_code == module.code
    )
    if not user.is_admin:
        stmt = stmt.where(
            or_(
                ImportBatch.released.is_(True),
                ImportBatch.id.in_(enabled_batch_ids(db, user)),
                ImportBatch.imported_by == user.id,
            )
        )
    return list(db.execute(stmt.order_by(ImportBatch.source)).scalars())


def visible_labs(db: Session, user: User):
    stmt = select(Lab)
    if user.is_admin:
        return stmt
    return stmt.where(Lab.visibility == "public")


# --------------------------------------------------------------------- modules


def all_modules(db: Session) -> list[Module]:
    return list(
        db.execute(
            select(Module)
            .options(selectinload(Module.topics).selectinload(Topic.objectives))
            .order_by(Module.position, Module.code)
        ).scalars()
    )


def module_by_code(db: Session, code: str) -> Module | None:
    return db.execute(
        select(Module)
        .options(selectinload(Module.topics).selectinload(Topic.objectives))
        .where(Module.code == code)
    ).scalar_one_or_none()


def user_modules(db: Session, user: User) -> list[UserModule]:
    return list(
        db.execute(
            select(UserModule)
            .options(selectinload(UserModule.module))
            .where(UserModule.user_id == user.id)
            .order_by(UserModule.selected_at)
        ).scalars()
    )


def user_module(db: Session, user: User, module: Module) -> UserModule | None:
    return db.execute(
        select(UserModule).where(UserModule.user_id == user.id, UserModule.module_id == module.id)
    ).scalar_one_or_none()


# -------------------------------------------------------------------- progress


@dataclass
class ObjectiveProgress:
    objective: Objective
    total: int = 0
    answered: int = 0
    correct: int = 0
    with_help: int = 0

    @property
    def percent_correct(self) -> int:
        return round(100 * self.correct / self.total) if self.total else 0

    @property
    def percent_answered(self) -> int:
        return round(100 * self.answered / self.total) if self.total else 0


@dataclass
class ModuleProgress:
    module: Module
    total: int = 0
    answered: int = 0
    correct: int = 0
    with_help: int = 0
    topics: dict[str, list[ObjectiveProgress]] = field(default_factory=dict)
    exams: list[Exam] = field(default_factory=list)
    labs_total: int = 0
    labs_done: int = 0

    @property
    def percent_correct(self) -> int:
        return round(100 * self.correct / self.total) if self.total else 0

    @property
    def percent_answered(self) -> int:
        return round(100 * self.answered / self.total) if self.total else 0

    @property
    def help_rate(self) -> int:
        return round(100 * self.with_help / self.answered) if self.answered else 0

    @property
    def best_exam(self) -> Exam | None:
        finished = [e for e in self.exams if e.finished_at and e.mode == "exam"]
        return max(finished, key=lambda e: e.percent) if finished else None


def latest_attempts(db: Session, user: User, question_ids: list[int]) -> dict[int, Attempt]:
    """Return the most recent practice/exam attempt per question."""
    if not question_ids:
        return {}
    rows = db.execute(
        select(Attempt)
        .where(
            Attempt.user_id == user.id,
            Attempt.question_id.in_(question_ids),
            Attempt.mode != "entry",
        )
        .order_by(Attempt.answered_at, Attempt.id)
    ).scalars()
    latest: dict[int, Attempt] = {}
    for a in rows:
        latest[a.question_id] = a
    return latest


def help_usage(db: Session, user: User, question_ids: list[int]) -> set[int]:
    if not question_ids:
        return set()
    rows = db.execute(
        select(Attempt.question_id).where(
            Attempt.user_id == user.id,
            Attempt.question_id.in_(question_ids),
            Attempt.used_help.is_(True),
        )
    ).scalars()
    return set(rows)


def module_progress(db: Session, user: User, module: Module) -> ModuleProgress:
    progress = ModuleProgress(module=module)
    questions = list(
        db.execute(visible_questions(db, user).where(Question.module_id == module.id)).scalars()
    )
    qids = [q.id for q in questions]
    latest = latest_attempts(db, user, qids)
    helped = help_usage(db, user, qids)
    by_objective: dict[int | None, list[Question]] = defaultdict(list)
    for q in questions:
        by_objective[q.objective_id].append(q)
    for topic in module.topics:
        entries = []
        for objective in topic.objectives:
            op = ObjectiveProgress(objective=objective)
            for q in by_objective.get(objective.id, []):
                op.total += 1
                a = latest.get(q.id)
                if a is not None:
                    op.answered += 1
                    op.correct += int(a.is_correct)
                if q.id in helped:
                    op.with_help += 1
            entries.append(op)
            progress.total += op.total
            progress.answered += op.answered
            progress.correct += op.correct
            progress.with_help += op.with_help
        progress.topics[topic.code] = entries
    for q in by_objective.get(None, []):
        progress.total += 1
        a = latest.get(q.id)
        if a is not None:
            progress.answered += 1
            progress.correct += int(a.is_correct)
    progress.exams = list(
        db.execute(
            select(Exam)
            .where(
                Exam.user_id == user.id, Exam.module_id == module.id, Exam.finished_at.is_not(None)
            )
            .order_by(Exam.finished_at.desc())
        ).scalars()
    )
    lab_stmt = select(Lab.id).where(Lab.module_id == module.id)
    if not user.is_admin:
        lab_stmt = lab_stmt.where(Lab.visibility == "public")
    lab_ids = list(db.execute(lab_stmt).scalars())
    progress.labs_total = len(lab_ids)
    if lab_ids:
        progress.labs_done = db.execute(
            select(func.count(LabProgress.id)).where(
                LabProgress.user_id == user.id, LabProgress.lab_id.in_(lab_ids)
            )
        ).scalar_one()
    return progress


# --------------------------------------------------------------- question choice


def pick_practice_question(
    db: Session,
    user: User,
    module: Module,
    objective: Objective | None = None,
    exclude_id: int | None = None,
    pool: str = "all",
) -> Question | None:
    """Pick the next practice question: unanswered first, then wrong ones, then any.

    ``pool`` restricts the selection to "core" (bundled and regular imports) or "extra"
    (supplementary pools enabled for the user).
    """
    stmt = visible_questions(db, user).where(Question.module_id == module.id)
    if objective is not None:
        stmt = stmt.where(Question.objective_id == objective.id)
    if pool == "extra":
        stmt = stmt.where(Question.supplementary.is_(True))
    elif pool == "core":
        stmt = stmt.where(Question.supplementary.is_(False))
    questions = list(db.execute(stmt).scalars())
    if exclude_id is not None and len(questions) > 1:
        questions = [q for q in questions if q.id != exclude_id]
    if not questions:
        return None
    latest = latest_attempts(db, user, [q.id for q in questions])
    unanswered = [q for q in questions if q.id not in latest]
    if unanswered:
        return random.choice(unanswered)
    wrong = [q for q in questions if not latest[q.id].is_correct]
    if wrong:
        return random.choice(wrong)
    return random.choice(questions)


def select_exam_questions(
    db: Session, user: User, module: Module, count: int, topic: Topic | None = None
) -> list[int]:
    """Random question ids, spread across topics roughly by their exam weight."""
    stmt = visible_questions(db, user).where(Question.module_id == module.id)
    if topic is not None:
        objective_ids = [o.id for o in topic.objectives]
        stmt = stmt.where(Question.objective_id.in_(objective_ids))
    questions = list(db.execute(stmt).scalars())
    if len(questions) <= count:
        random.shuffle(questions)
        return [q.id for q in questions]
    if topic is not None:
        sample = random.sample(questions, count)
        return [q.id for q in sample]
    objective_topic = {o.id: t for t in module.topics for o in t.objectives}
    buckets: dict[str, list[Question]] = defaultdict(list)
    for q in questions:
        t = objective_topic.get(q.objective_id)
        buckets[t.code if t else "other"].append(q)
    weights = {t.code: t.weight for t in module.topics}
    total_weight = sum(weights.get(code, 1) for code in buckets)
    chosen: list[Question] = []
    for code, bucket in buckets.items():
        share = round(count * weights.get(code, 1) / total_weight)
        random.shuffle(bucket)
        chosen.extend(bucket[:share])
    remaining = [q for q in questions if q not in chosen]
    random.shuffle(remaining)
    while len(chosen) < count and remaining:
        chosen.append(remaining.pop())
    chosen = chosen[:count]
    random.shuffle(chosen)
    return [q.id for q in chosen]


def grade(question: Question, selected: set[int]) -> bool:
    return selected == question.correct_choice_ids and bool(selected)


# ----------------------------------------------------------------------- terms


_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _term_pattern(term: str) -> re.Pattern[str]:
    """Compiled whole-word pattern for a glossary term (cached; compiling 270 patterns
    per request was the main cost of the practice page)."""
    pattern = _PATTERN_CACHE.get(term)
    if pattern is None:
        pattern = re.compile(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])")
        _PATTERN_CACHE[term] = pattern
    return pattern


def terms_for_question(db: Session, question: Question) -> list[Term]:
    """Linked terms plus glossary terms that occur literally in the question text."""
    text = " ".join([question.text_en, *[c.text_en for c in question.choices]]).lower()
    linked = {t.id: t for t in question.terms}
    all_terms = db.execute(select(Term)).scalars()
    for term in all_terms:
        if term.id in linked:
            continue
        if _term_pattern(term.term).search(text):
            linked[term.id] = term
    return sorted(linked.values(), key=lambda t: -len(t.term))


def user_term_status(db: Session, user: User, term_ids: list[int]) -> dict[int, str]:
    if not term_ids:
        return {}
    rows = db.execute(
        select(UserTerm).where(UserTerm.user_id == user.id, UserTerm.term_id.in_(term_ids))
    ).scalars()
    return {r.term_id: r.status for r in rows}


def record_attempt(
    db: Session,
    user: User,
    question: Question,
    is_correct: bool,
    used_help: bool,
    mode: str = MODE_PRACTICE,
    exam_id: int | None = None,
) -> Attempt:
    attempt = Attempt(
        user_id=user.id,
        question_id=question.id,
        mode=mode,
        is_correct=is_correct,
        used_help=used_help,
        exam_id=exam_id,
    )
    db.add(attempt)
    db.flush()
    return attempt
