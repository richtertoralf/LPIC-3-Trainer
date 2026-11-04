"""Alembic environment. Uses the application's settings and models."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context

from app.config import get_settings
from app.db import build_engine
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    override = config.get_main_option("sqlalchemy.url")
    return override or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = config.attributes.get("connection")
    if connectable is not None:
        connectable.connection.execute("PRAGMA foreign_keys=OFF")
        context.configure(
            connection=connectable, target_metadata=target_metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    engine = build_engine(_url())
    with engine.connect() as connection:
        # SQLite "move and copy" table rebuilds drop the old table. With foreign keys enabled
        # that fires ON DELETE actions on child rows (NULLed question links, cascaded group
        # releases). Foreign keys must be off while migrations run (SQLite documentation,
        # "Making Other Kinds Of Table Schema Changes").
        # The PRAGMA goes through the DBAPI connection so that it does not open a SQLAlchemy
        # transaction that would swallow Alembic's commit.
        connection.connection.execute("PRAGMA foreign_keys=OFF")
        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()
        connection.connection.execute("PRAGMA foreign_keys=ON")
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
