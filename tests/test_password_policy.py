"""Configurable password length policy (LPIC3_PASSWORD_MIN_LENGTH / _MAX_LENGTH).

The policy is read from the environment at request time, so the tests switch it with
monkeypatch + reset_settings on the shared application instance.
"""

from __future__ import annotations

import json
from urllib.parse import unquote

import pytest

from app.config import Settings, reset_settings
from app.security import generate_password, password_error
from app.web import FLASH_COOKIE
from tests.conftest import login, register, unique


def flash(response) -> str:
    """Text of the flash message set by a redirect."""
    raw = response.cookies.get(FLASH_COOKIE)
    assert raw, "no flash message"
    return json.loads(unquote(raw))["text"]


@pytest.fixture
def policy(monkeypatch):
    def apply(minimum: int | None = None, maximum: int | None = None) -> None:
        for name, value in (
            ("LPIC3_PASSWORD_MIN_LENGTH", minimum),
            ("LPIC3_PASSWORD_MAX_LENGTH", maximum),
        ):
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, str(value))
        reset_settings()

    yield apply
    monkeypatch.delenv("LPIC3_PASSWORD_MIN_LENGTH", raising=False)
    monkeypatch.delenv("LPIC3_PASSWORD_MAX_LENGTH", raising=False)
    reset_settings()


def test_defaults_keep_previous_behaviour(policy):
    policy()
    assert Settings().password_min_length == 8
    assert Settings().password_max_length == 128
    assert password_error("kurz") == "Das Passwort muss mindestens 8 Zeichen lang sein."
    assert password_error("achtzeic") is None
    assert password_error("x" * 128) is None
    assert password_error("x" * 129) == "Das Passwort darf höchstens 128 Zeichen lang sein."


def test_invalid_configuration_is_reported_clearly(policy):
    policy(0)
    with pytest.raises(ValueError, match="LPIC3_PASSWORD_MIN_LENGTH"):
        Settings()
    policy(10, 6)
    with pytest.raises(ValueError, match="LPIC3_PASSWORD_MAX_LENGTH"):
        Settings()
    policy(6, 5000)
    with pytest.raises(ValueError, match="1024"):
        Settings()


def test_registration_uses_configured_limits(client, admin, policy):
    policy(6, 24)
    name = unique("pw")
    r = client.post("/register", data={"username": name, "password": "abcde", "password2": "abcde"})
    assert r.status_code == 400 and "mindestens 6 Zeichen" in r.text
    long = "a" * 25
    r = client.post("/register", data={"username": name, "password": long, "password2": long})
    assert r.status_code == 400 and "höchstens 24 Zeichen" in r.text
    ok = {"username": name, "password": "abcdef", "password2": "abcdef"}
    r = client.post("/register", data=ok)
    assert r.status_code == 303
    # the form tells the browser the same limits
    client.cookies.clear()
    page = client.get("/register").text
    assert 'minlength="6"' in page and 'maxlength="24"' in page
    assert "Mindestens 6 Zeichen, höchstens 24." in page


def test_existing_accounts_survive_a_stricter_policy(client, admin, policy):
    policy()
    name = unique("old")
    register(client, name, "geheim123")  # 9 characters under the default policy
    policy(12, 64)
    login(client, name, "geheim123")
    r = client.get("/account")
    assert r.status_code == 200, "login must still work with the old shorter password"
    # changing the password now follows the new policy
    r = client.post(
        "/account/password",
        data={"current_password": "geheim123", "password": "neu12345", "password2": "neu12345"},
    )
    assert r.status_code == 303 and flash(r) == "Das Passwort muss mindestens 12 Zeichen lang sein."
    r = client.post(
        "/account/password",
        data={
            "current_password": "geheim123",
            "password": "zwoelfzeichen",
            "password2": "zwoelfzeichen",
        },
    )
    assert r.status_code == 303 and flash(r).startswith("Passwort geändert")


def test_admin_user_creation_and_reset_follow_policy(client, admin, policy):
    policy(10, 16)
    name = unique("neu")
    form = {"username": name, "role": "learner"}
    r = admin.post("/admin/users", data={**form, "password": "kurz12345"})
    assert r.status_code == 303 and flash(r) == "Das Passwort muss mindestens 10 Zeichen lang sein."
    r = admin.post("/admin/users", data={**form, "password": "a" * 17})
    assert r.status_code == 303 and flash(r) == "Das Passwort darf höchstens 16 Zeichen lang sein."
    r = admin.post("/admin/users", data={**form, "password": "startpasswort1"})
    assert r.status_code == 303 and "angelegt" in flash(r)
    for _ in range(20):
        assert 12 <= len(generate_password()) <= 16
    policy(20, 24)
    assert all(20 <= len(generate_password()) <= 24 for _ in range(20))
    policy(4, 8)
    assert all(len(generate_password()) == 8 for _ in range(20))


def test_cli_user_commands_follow_policy(tmp_path):
    import os
    import subprocess
    import sys

    env = {
        "LPIC3_DATA_DIR": str(tmp_path),
        "LPIC3_PASSWORD_MIN_LENGTH": "6",
        "LPIC3_PASSWORD_MAX_LENGTH": "10",
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
    }

    def cli(*args):
        return subprocess.run(
            [sys.executable, "-m", "app.cli", *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )

    r = cli("user", "create", "sechs", "--password", "abcde")
    assert r.returncode == 1 and "mindestens 6 Zeichen" in r.stderr
    r = cli("user", "create", "sechs", "--password", "abcdefghijk")
    assert r.returncode == 1 and "höchstens 10 Zeichen" in r.stderr
    r = cli("user", "create", "sechs", "--password", "abcdef")
    assert r.returncode == 0, r.stderr
    r = cli("user", "set-password", "sechs", "--password", "abc")
    assert r.returncode == 1 and "mindestens 6 Zeichen" in r.stderr
    env["LPIC3_PASSWORD_MAX_LENGTH"] = "3"
    r = cli("user", "list")
    assert r.returncode != 0 and "LPIC3_PASSWORD_MAX_LENGTH" in r.stderr
