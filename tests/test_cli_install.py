"""Install, upgrade, rollback, uninstall and purge with stubbed system commands.

The real commands need root and systemd. The test runs the complete lpic3ctl flow in a
temporary directory tree with LPIC3_UNPRIVILEGED_TEST=1 and stub binaries for useradd,
userdel and systemctl, so every file system step and the command sequence are verified.
"""

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import PROJECT_DIR

STUBS = {
    "useradd": '#!/bin/sh\necho "useradd $*" >> "$STUB_LOG"\n',
    "userdel": '#!/bin/sh\necho "userdel $*" >> "$STUB_LOG"\n',
    "systemctl": (
        '#!/bin/sh\necho "systemctl $*" >> "$STUB_LOG"\n'
        'case "$1" in is-active) echo inactive;; is-enabled) echo enabled;; esac\nexit 0\n'
    ),
}


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    root = tmp_path_factory.mktemp("install")
    stub_dir = root / "stubs"
    stub_dir.mkdir()
    for name, body in STUBS.items():
        path = stub_dir / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    for d in ("systemd", "bin"):
        (root / d).mkdir()
    return {
        "PATH": f"{stub_dir}:{os.environ.get('PATH', '')}",
        "LANG": "C.UTF-8",
        "HOME": os.environ.get("HOME", "/tmp"),
        "STUB_LOG": str(root / "stub.log"),
        "LPIC3_UNPRIVILEGED_TEST": "1",
        "LPIC3_INSTALL_DIR": str(root / "opt"),
        "LPIC3_CONFIG_DIR": str(root / "etc"),
        "LPIC3_DATA_DIR": str(root / "var"),
        "LPIC3_SYSTEMD_DIR": str(root / "systemd"),
        "LPIC3_BIN_DIR": str(root / "bin"),
        "LPIC3_PORT": "18765",
        "_root": str(root),
    }


def cli(env, *args, input_text=None):
    clean = {k: v for k, v in env.items() if not k.startswith("_")}
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        capture_output=True,
        text=True,
        env=clean,
        cwd=PROJECT_DIR,
        input=input_text,
        timeout=600,
    )


def stub_log(env) -> str:
    path = Path(env["STUB_LOG"])
    return path.read_text() if path.exists() else ""


def test_01_install(env):
    root = Path(env["_root"])
    r = cli(env, "install", "--source", str(PROJECT_DIR))
    assert r.returncode == 0, r.stdout + r.stderr
    assert (root / "opt" / "app" / "pyproject.toml").is_file()
    assert (root / "opt" / "app" / "content" / "objectives" / "303.json").is_file()
    assert not (root / "opt" / "app" / ".git").exists()
    assert (root / "opt" / "venv" / "bin" / "lpic3ctl").is_file()
    assert (root / "etc" / "lpic3-trainer.env").is_file()
    assert (root / "var" / "lpic3-trainer.db").is_file()
    assert (root / "var" / "backups").is_dir()
    unit = (root / "systemd" / "lpic3-trainer.service").read_text()
    assert "ExecStart=/opt/lpic3-trainer/venv/bin/lpic3ctl serve" in unit
    assert (root / "bin" / "lpic3ctl").is_symlink()
    log = stub_log(env)
    assert "useradd --system" in log and "systemctl enable lpic3-trainer" in log
    assert "systemctl restart lpic3-trainer" in log
    # the installed CLI works on its own and finds content and migrations
    r = subprocess.run(
        [str(root / "opt" / "venv" / "bin" / "lpic3ctl"), "check"],
        capture_output=True,
        text=True,
        env={k: v for k, v in env.items() if not k.startswith("_")},
    )
    assert "[OK] Schema aktuell" in r.stdout and "[OK] Inhaltsdateien gültig" in r.stdout, r.stdout


def test_02_install_twice_is_refused(env):
    r = cli(env, "install", "--source", str(PROJECT_DIR))
    assert r.returncode == 2 and "bereits eine Installation" in r.stdout


def test_03_upgrade_keeps_config_and_creates_backup(env):
    root = Path(env["_root"])
    env_file = root / "etc" / "lpic3-trainer.env"
    env_file.write_text(env_file.read_text() + "# local change\n")
    r = cli(env, "upgrade", "--source", str(PROJECT_DIR))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "# local change" in env_file.read_text()
    assert list((root / "var" / "backups").glob("lpic3-trainer-backup-*.tar.gz"))
    assert (root / "opt" / "app.previous").is_dir()
    assert "systemctl restart lpic3-trainer" in stub_log(env)


def test_04_rollback(env):
    root = Path(env["_root"])
    r = cli(env, "rollback")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (root / "opt" / "app.failed").is_dir() and not (root / "opt" / "app.previous").exists()
    assert (root / "opt" / "app" / "pyproject.toml").is_file()


def test_05_status_and_version(env):
    r = cli(env, "status")
    assert r.returncode == 0 and "Schema:" in r.stdout
    r = cli(env, "version")
    assert r.returncode == 0 and "Installiert:" in r.stdout


def test_06_uninstall_keeps_data(env):
    root = Path(env["_root"])
    r = cli(env, "uninstall")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (root / "opt").exists()
    assert not (root / "systemd" / "lpic3-trainer.service").exists()
    assert not (root / "bin" / "lpic3ctl").exists()
    assert (root / "var" / "lpic3-trainer.db").is_file()
    assert (root / "etc" / "lpic3-trainer.env").is_file()
    assert "systemctl disable --now lpic3-trainer" in stub_log(env)


def test_07_purge_requires_confirmation(env):
    root = Path(env["_root"])
    r = cli(env, "purge", input_text="nein\n")
    assert r.returncode == 2 and (root / "var").exists()
    r = cli(env, "purge", "--yes")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (root / "var").exists() and not (root / "etc").exists()
    # userdel is only called when the system user exists (not the case with stubs)
