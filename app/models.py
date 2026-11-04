"""SQLAlchemy ORM models.

Shared learning content (modules, objectives, questions, terms, labs) and personal data
(users, sessions, attempts, progress) live in separate tables.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

ROLE_ADMIN = "admin"
ROLE_SUPERVISOR = "supervisor"
ROLE_LEARNER = "learner"
ROLES = (ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_LEARNER)

STATUS_ACTIVE = "active"
STATUS_PENDING = "pending"
STATUS_DISABLED = "disabled"

MODE_PRACTICE = "practice"
MODE_EXAM = "exam"
MODE_ENTRY = "entry"
MODE_VOCAB = "vocab"


def utcnow() -> datetime:
    return datetime.now(UTC).replace(microsecond=0, tzinfo=None)


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------------- users


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default=ROLE_LEARNER)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def is_supervisor(self) -> bool:
        return self.role in (ROLE_ADMIN, ROLE_SUPERVISOR)

    @property
    def label(self) -> str:
        return self.display_name or self.username


class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped[User] = relationship(back_populates="sessions")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    join_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="approval")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    members: Mapped[list[GroupMember]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="member")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_ACTIVE)
    joined_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    group: Mapped[Group] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class GroupSource(Base):
    """A supplementary import batch enabled for the members of a group by a supervisor."""

    __tablename__ = "group_sources"
    __table_args__ = (UniqueConstraint("group_id", "batch_id", name="uq_group_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False
    )
    enabled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    enabled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


# ------------------------------------------------------------------- learning content


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    title_de: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    description_de: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    source_url: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    topics: Mapped[list[Topic]] = relationship(
        back_populates="module", cascade="all, delete-orphan", order_by="Topic.code"
    )


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    title_de: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    module: Mapped[Module] = relationship(back_populates="topics")
    objectives: Mapped[list[Objective]] = relationship(
        back_populates="topic", cascade="all, delete-orphan", order_by="Objective.code"
    )

    @property
    def weight(self) -> int:
        return sum(o.weight for o in self.objectives)


class Objective(Base):
    __tablename__ = "objectives"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    title_de: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    summary_de: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tools: Mapped[str] = mapped_column(Text, nullable=False, default="")

    topic: Mapped[Topic] = relationship(back_populates="objectives")


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="questions")
    module_code: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    license: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    author: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="private")
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    bundled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # External (imported) pools stay unreleased until a supervisor enables them for a group
    # or an administrator releases them system-wide. Bundled project content is released.
    supplementary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    released: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    source_url: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    exam_code: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    exam_version: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    rights: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    objective_id: Mapped[int | None] = mapped_column(
        ForeignKey("objectives.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="single")
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    text_de: Mapped[str] = mapped_column(Text, nullable=False, default="")
    explanation_de: Mapped[str] = mapped_column(Text, nullable=False, default="")
    explanation_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Optional documentation reference backing the correct answer (man page, project docs).
    reference: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="public")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    supplementary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL")
    )
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    module: Mapped[Module] = relationship()
    objective: Mapped[Objective | None] = relationship()
    choices: Mapped[list[Choice]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="Choice.position"
    )
    terms: Mapped[list[Term]] = relationship(secondary="question_terms")
    batch: Mapped[ImportBatch | None] = relationship()

    @property
    def correct_choice_ids(self) -> set[int]:
        return {c.id for c in self.choices if c.is_correct}


class Choice(Base):
    __tablename__ = "choices"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    text_de: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    question: Mapped[Question] = relationship(back_populates="choices")


class Term(Base):
    __tablename__ = "terms"

    id: Mapped[int] = mapped_column(primary_key=True)
    term: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    translation_de: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation_de: Mapped[str] = mapped_column(Text, nullable=False, default="")


class QuestionTerm(Base):
    __tablename__ = "question_terms"

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    term_id: Mapped[int] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), primary_key=True
    )


class Lab(Base):
    __tablename__ = "labs"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    objective_id: Mapped[int | None] = mapped_column(
        ForeignKey("objectives.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    goal_de: Mapped[str] = mapped_column(Text, nullable=False, default="")
    environment_de: Mapped[str] = mapped_column(Text, nullable=False, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    checks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="public")
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL")
    )

    module: Mapped[Module] = relationship()
    objective: Mapped[Objective | None] = relationship()


# ----------------------------------------------------------------- personal progress


class UserModule(Base):
    __tablename__ = "user_modules"
    __table_args__ = (UniqueConstraint("user_id", "module_id", name="uq_user_module"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    selected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    entry_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    entry_result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    module: Mapped[Module] = relationship()


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default=MODE_PRACTICE)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    used_help: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exam_id: Mapped[int | None] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"))
    answered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    question: Mapped[Question] = relationship()


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default=MODE_EXAM)
    question_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    answers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    module: Mapped[Module] = relationship()
    topic: Mapped[Topic | None] = relationship()

    @property
    def percent(self) -> int:
        return round(100 * self.correct_count / self.total_count) if self.total_count else 0

    @property
    def passed(self) -> bool:
        # LPI exams use scaled scores; 500 of 800 roughly corresponds to 60 % correct.
        return self.percent >= 60


class UserTerm(Base):
    __tablename__ = "user_terms"
    __table_args__ = (UniqueConstraint("user_id", "term_id", name="uq_user_term"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="learning")
    reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    term: Mapped[Term] = relationship()


class LabProgress(Base):
    __tablename__ = "lab_progress"
    __table_args__ = (UniqueConstraint("user_id", "lab_id", name="uq_lab_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    lab: Mapped[Lab] = relationship()
