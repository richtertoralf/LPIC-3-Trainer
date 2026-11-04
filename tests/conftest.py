"""Shared pytest fixtures: isolated test database, test client and helpers."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TMP = tempfile.mkdtemp(prefix="lpic3-test-")
os.environ["LPIC3_DATA_DIR"] = _TMP
os.environ["LPIC3_SECURE_COOKIES"] = "false"
os.environ["LPIC3_EXAM_QUESTIONS"] = "12"
os.environ["LPIC3_TOPIC_EXAM_QUESTIONS"] = "5"
os.environ["LPIC3_ENTRY_QUESTIONS"] = "6"

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.content import sync_bundled_content  # noqa: E402
from app.db import session_scope  # noqa: E402
from app.main import app  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return Path(_TMP)


@pytest.fixture(scope="session")
def client() -> TestClient:
    """One application instance for the whole session; the lifespan runs migrations."""
    with TestClient(app, follow_redirects=False) as c:
        with session_scope() as db:
            sync_bundled_content(db, get_settings().content_dir)
        yield c


class Counter:
    value = 0


def unique(prefix: str) -> str:
    Counter.value += 1
    return f"{prefix}{Counter.value}"


def register(client: TestClient, username: str, password: str = "geheim123") -> None:
    r = client.post(
        "/register", data={"username": username, "password": password, "password2": password}
    )
    assert r.status_code in (200, 303), r.text


def login(client: TestClient, username: str, password: str = "geheim123") -> None:
    client.cookies.clear()
    r = client.post("/login", data={"username": username, "password": password})
    assert r.status_code == 303, r.text


def new_client(username: str | None = None, password: str = "geheim123") -> TestClient:
    """Fresh client with its own cookie jar, optionally registered and logged in."""
    c = TestClient(app, follow_redirects=False)
    if username:
        register(c, username, password)
        login(c, username, password)
    return c


@pytest.fixture(scope="session")
def admin(client) -> TestClient:
    """The first registered user becomes administrator."""
    c = new_client(unique("admin"))
    assert c.get("/api/me").json()["role"] == "admin"
    return c


@pytest.fixture
def learner(client, admin) -> TestClient:
    return new_client(unique("learner"))
