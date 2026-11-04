"""SQLite engine and session handling (WAL mode, short write transactions)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _configure_sqlite(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=15000")
    cursor.close()


def build_engine(database_url: str) -> Engine:
    """Create a SQLite engine with the project PRAGMA settings."""
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _configure_sqlite)
    return engine


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine = build_engine(settings.database_url)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def reset_engine() -> None:
    """Dispose the engine so the next access creates a fresh one (tests, CLI)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def begin_write(session: Session) -> None:
    """Start the SQLite transaction as a write transaction (BEGIN IMMEDIATE).

    pysqlite opens deferred transactions. A request that reads first and writes later
    would have to upgrade its lock; if another writer committed meanwhile, SQLite fails
    immediately with "database is locked" without honouring busy_timeout. Taking the
    write lock up front makes concurrent writers queue correctly instead.
    """
    session.execute(text("BEGIN IMMEDIATE"))


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope for a short unit of work (writes allowed)."""
    session = get_session_factory()()
    try:
        begin_write(session)
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def db_health() -> dict:
    """Return basic health information about the database."""
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        journal = conn.execute(text("PRAGMA journal_mode")).scalar()
    return {"ok": True, "schema_version": version, "journal_mode": journal}
