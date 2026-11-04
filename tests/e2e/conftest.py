"""Playwright end-to-end tests against a real uvicorn server with its own test database."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def server():
    """Start the application in a subprocess with a fresh database and bundled content."""
    data_dir = tempfile.mkdtemp(prefix="lpic3-e2e-")
    port = _free_port()
    env = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
        "LPIC3_DATA_DIR": data_dir,
        "LPIC3_PORT": str(port),
        "LPIC3_HOST": "127.0.0.1",
        "LPIC3_EXAM_QUESTIONS": "6",
        "LPIC3_TOPIC_EXAM_QUESTIONS": "3",
        "LPIC3_ENTRY_QUESTIONS": "4",
        "LPIC3_LOG_LEVEL": "warning",
    }
    log = open(Path(data_dir) / "server.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.cli", "serve"],
        env=env,
        cwd=PROJECT_DIR,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            break
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError(
                    "server exited: " + Path(data_dir, "server.log").read_text()
                ) from None
            time.sleep(0.5)
    else:
        raise RuntimeError("server did not start")
    yield {"base": base, "data_dir": data_dir}
    proc.terminate()
    proc.wait(timeout=10)
    log.close()


class Counter:
    n = 0


@pytest.fixture
def username() -> str:
    Counter.n += 1
    return f"e2e{Counter.n}_{int(time.time()) % 100000}"


@pytest.fixture
def browser_errors(page):
    """Collect JavaScript errors and failed requests; the test fails if any occurred."""
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    # Expected HTTP error pages (wrong password, 403 for learners) are logged by the browser as
    # "Failed to load resource"; those are intentional and not JavaScript errors.
    page.on(
        "console",
        lambda m: (
            errors.append(f"console.error: {m.text}")
            if m.type == "error" and "Failed to load resource" not in m.text
            else None
        ),
    )
    page.on("requestfailed", lambda r: errors.append(f"requestfailed: {r.url} ({r.failure})"))
    yield errors
    assert not errors, "\n".join(errors)


def register(page, base: str, username: str, password: str = "geheim123") -> None:
    page.goto(base + "/register")
    page.fill("input[name=username]", username)
    page.fill("input[name=password]", password)
    page.fill("input[name=password2]", password)
    page.click("form[action='/register'] button[type=submit]")
    page.wait_for_load_state("networkidle")


def login(page, base: str, username: str, password: str = "geheim123") -> None:
    page.goto(base + "/login")
    page.fill("input[name=username]", username)
    page.fill("input[name=password]", password)
    page.click("form[action='/login'] button[type=submit]")
    page.wait_for_load_state("networkidle")


def select_module(page, base: str, code: str) -> None:
    page.goto(base + "/modules")
    page.locator(f"form:has(input[value='{code}']) button[type=submit]").click()
    page.wait_for_load_state("networkidle")


@pytest.fixture(scope="session")
def admin_credentials(server, browser):
    """Registers the very first account (administrator) through the real browser once."""
    name = "e2eadmin"
    context = browser.new_context()
    page = context.new_page()
    register(page, server["base"], name)
    assert page.url.rstrip("/") in (server["base"], server["base"] + "/modules")
    context.close()
    return {"username": name, "password": "geheim123"}


@pytest.fixture
def question_file(tmp_path) -> Path:
    doc = {
        "schema_version": 1,
        "kind": "questions",
        "module": "303",
        "license": "Test",
        "source": f"E2E-Quelle {int(time.time())}",
        "exam_version": "3.0",
        "questions": [
            {
                "id": f"e2e-q-{int(time.time() * 1000)}",
                "objective": "331.1",
                "type": "single",
                "question": "Which command signs a certificate request with a CA?",
                "question_de": "Welcher Befehl signiert einen Zertifikatsantrag mit einer CA?",
                "choices": [
                    {"text": "openssl ca", "text_de": "openssl ca", "correct": True},
                    {"text": "openssl genrsa", "text_de": "openssl genrsa"},
                ],
                "explanation_de": "openssl ca signiert Anträge.",
            }
        ],
    }
    path = tmp_path / "e2e-questions.json"
    path.write_text(json.dumps(doc))
    return path
