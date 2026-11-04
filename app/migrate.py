"""Programmatic Alembic access used by the application startup and lpic3ctl."""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from app.config import PROJECT_DIR, get_settings
from app.db import get_engine

ALEMBIC_INI = PROJECT_DIR / "alembic.ini"


def alembic_config() -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(PROJECT_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    return cfg


def upgrade_database() -> None:
    """Apply all pending migrations."""
    command.upgrade(alembic_config(), "head")


def current_revision() -> str | None:
    with get_engine().connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def head_revision() -> str | None:
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def is_up_to_date() -> bool:
    return current_revision() == head_revision()
