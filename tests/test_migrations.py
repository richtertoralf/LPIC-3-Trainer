"""Schema migrations: upgrade from the first revision with existing data, roundtrip downgrade."""

import os
import sqlite3
import subprocess
import sys

from tests.conftest import PROJECT_DIR


def alembic(env, *args):
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=PROJECT_DIR,
        timeout=300,
    )


def test_upgrade_from_initial_schema_migrates_existing_data(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    env = {"LPIC3_DATA_DIR": str(data_dir), "PATH": os.environ.get("PATH", "")}
    assert alembic(env, "upgrade", "0001").returncode == 0
    db = sqlite3.connect(data_dir / "lpic3-trainer.db")
    db.execute(
        "INSERT INTO import_batches (id, filename, kind, module_code, license, author, visibility,"
        " item_count, imported_at, bundled, checksum) VALUES "
        "(1, 'core.json', 'questions', '303', 'CC', '', 'public', 1, '2026-01-01', 1, 'x'),"
        "(2, 'teacher.json', 'questions', '303', '', '', 'private', 1, '2026-01-01', 0, 'y')"
    )
    db.execute(
        "INSERT INTO modules (id, code, title, title_de, description_de, version, source_url,"
        " position) VALUES (1, '303', 'S', '', '', '3.0', '', 1)"
    )
    db.execute(
        "INSERT INTO questions (id, external_id, module_id, kind, text_en, text_de, explanation_de,"
        " explanation_en, difficulty, visibility, is_active, import_batch_id, created_at) VALUES "
        "(1, 'q1', 1, 'single', 'Q1', '', '', '', 2, 'public', 1, 1, '2026-01-01'),"
        "(2, 'q2', 1, 'single', 'Q2', '', '', '', 2, 'private', 1, 2, '2026-01-01')"
    )
    db.commit()
    db.close()
    r = alembic(env, "upgrade", "head")
    assert r.returncode == 0, r.stderr
    db = sqlite3.connect(data_dir / "lpic3-trainer.db")
    rows = {
        r[0]: r[1:]
        for r in db.execute(
            "SELECT filename, supplementary, released, exam_code, exam_version, source_url, rights"
            " FROM import_batches"
        )
    }
    assert rows["core.json"] == (0, 1, "303-300", "3.0", "", "unknown")
    assert rows["teacher.json"] == (1, 0, "303-300", "3.0", "", "unknown")
    q = dict(db.execute("SELECT external_id, supplementary FROM questions"))
    assert q == {"q1": 0, "q2": 1}
    # table rebuilds must not fire ON DELETE actions on child rows (foreign keys off)
    links = dict(db.execute("SELECT external_id, import_batch_id FROM questions"))
    assert links == {"q1": 1, "q2": 2}
    assert db.execute("SELECT COUNT(*) FROM group_sources").fetchone()[0] == 0
    assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0004"
    db.close()


def test_downgrade_and_upgrade_roundtrip(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    env = {"LPIC3_DATA_DIR": str(data_dir), "PATH": os.environ.get("PATH", "")}
    assert alembic(env, "upgrade", "0002").returncode == 0
    db = sqlite3.connect(data_dir / "lpic3-trainer.db")
    db.execute(
        "INSERT INTO users (id, username, display_name, password_hash, role, status,"
        " created_at) VALUES (1, 'u', '', 'x', 'admin', 'active', '2026-01-01')"
    )
    db.execute(
        "INSERT INTO groups (id, name, description, join_mode, created_by, created_at)"
        " VALUES (1, 'g', '', 'open', 1, '2026-01-01')"
    )
    db.execute(
        "INSERT INTO import_batches (id, filename, kind, module_code, license, author, visibility,"
        " item_count, imported_at, bundled, checksum, supplementary, source, rights) VALUES "
        "(1, 'ext.json', 'questions', '303', '', '', 'private', 1, '2026-01-01', 0, 'x', 1,"
        " 'S', 'unknown')"
    )
    db.execute(
        "INSERT INTO group_sources (id, group_id, batch_id, enabled_by, enabled_at)"
        " VALUES (1, 1, 1, 1, '2026-01-01')"
    )
    db.commit()
    db.close()
    assert alembic(env, "upgrade", "head").returncode == 0
    db = sqlite3.connect(data_dir / "lpic3-trainer.db")
    assert db.execute("SELECT COUNT(*) FROM group_sources").fetchone()[0] == 1, "group release lost"
    db.close()
    assert alembic(env, "downgrade", "base").returncode == 0
    r = alembic(env, "upgrade", "head")
    assert r.returncode == 0, r.stderr
    db = sqlite3.connect(data_dir / "lpic3-trainer.db")
    cols = {r[1] for r in db.execute("PRAGMA table_info(import_batches)")}
    assert {
        "released",
        "exam_code",
        "exam_version",
        "source_url",
        "rights",
        "supplementary",
    } <= cols
    db.close()
