"""Install, upgrade, rollback, uninstall and purge with stubbed system commands.

The real commands need root and systemd. The test runs the complete lpic3ctl flow in a
temporary directory tree with LPIC3_UNPRIVILEGED_TEST=1 and stub binaries for useradd,
userdel and systemctl, so every file system step and the command sequence are verified.
"""

import os
import pwd
import re
import stat
import subprocess
import sys
import time
from datetime import datetime
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
    # codex-dev findings: no setuptools banner from the editable install, no Alembic INFO
    # lines in the administrator's output; the schema is reported in one line instead
    assert "BuildBackendWarning" not in r.stdout + r.stderr
    assert "[alembic" not in r.stdout + r.stderr and "Datenbankschema: " in r.stdout
    assert (root / "opt" / "app" / "pyproject.toml").is_file()
    assert (root / "opt" / "app" / "content" / "objectives" / "303.json").is_file()
    assert not (root / "opt" / "app" / ".git").exists()
    assert (root / "opt" / "venv" / "bin" / "lpic3ctl").is_file()
    assert (root / "etc" / "lpic3-trainer.env").is_file()
    assert (root / "var" / "lpic3-trainer.db").is_file()
    assert (root / "var" / "backups").is_dir()
    unit = (root / "systemd" / "lpic3-trainer.service").read_text()
    assert "ExecStart=/opt/lpic3-trainer/venv/bin/lpic3ctl serve" in unit
    assert "User=lpic3" in unit and "EnvironmentFile=/etc/lpic3-trainer/lpic3-trainer.env" in unit
    assert "ProtectSystem=strict" in unit and "ReadWritePaths=/var/lib/lpic3-trainer" in unit
    assert "WantedBy=multi-user.target" in unit
    assert "UMask=0027" in unit and "CapabilityBoundingSet=" in unit
    assert "SystemCallFilter=@system-service" in unit
    # file permissions: configuration not world readable, data directory private
    assert oct((root / "etc" / "lpic3-trainer.env").stat().st_mode)[-3:] == "640"
    assert oct((root / "etc").stat().st_mode)[-3:] == "750"
    assert oct((root / "var").stat().st_mode)[-3:] == "750"
    assert oct((root / "var" / "backups").stat().st_mode)[-3:] == "750"
    assert (root / "bin" / "lpic3ctl").is_symlink()
    build = (root / "opt" / "app" / "BUILD").read_text()
    assert "version=0." in build and "commit=" in build and "installed_at=" in build
    log = stub_log(env)
    try:
        pwd.getpwnam("lpic3")
    except KeyError:
        assert "useradd --system --home-dir" in log and "--shell /usr/sbin/nologin" in log
    else:  # the host already has the service account (real installation); useradd is skipped
        assert "useradd" not in log
    assert "systemctl daemon-reload" in log
    assert "systemctl enable lpic3-trainer" in log
    assert "systemctl restart lpic3-trainer" in log
    assert (
        log.index("daemon-reload")
        < log.index("enable lpic3-trainer")
        < log.index("restart lpic3-trainer")
    )
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
    before = stub_log(env)
    r = cli(env, "--upgrade", "--source", str(PROJECT_DIR))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "# local change" in env_file.read_text()
    assert list((root / "var" / "backups").glob("lpic3-trainer-backup-*.tar.gz"))
    assert (root / "opt" / "app.previous").is_dir()
    assert not (root / "opt" / "app.new").exists() and not (root / "opt" / "venv.new").exists()
    assert "geprüft" in r.stdout, "the new version is staged and probed before the swap"
    # the stub reports the service as inactive: a stopped service stays stopped (ADR-002)
    delta = stub_log(env)[len(before) :]
    assert "restart" not in delta and "start lpic3-trainer" not in delta, delta
    assert "bleibt gestoppt" in r.stdout


def test_03b_upgrade_installs_newest_stable_release_tag(env, tmp_path_factory):
    """Standard way: ``--upgrade`` without ``--source`` takes the newest tag vX.Y.Z of the
    remote (here a local bare clone), ignores pre-releases and does nothing when current."""
    root = Path(env["_root"])
    remote = tmp_path_factory.mktemp("remote") / "repo.git"
    subprocess.run(["git", "clone", "--quiet", "--bare", str(PROJECT_DIR), str(remote)], check=True)
    subprocess.run(["git", "-C", str(remote), "tag", "v99.0.0"], check=True)
    subprocess.run(["git", "-C", str(remote), "tag", "v99.1.0-rc1"], check=True)
    env2 = {**env, "LPIC3_UPGRADE_REMOTE": str(remote)}
    staged = time.time()
    r = cli(env2, "--upgrade")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "v99.0.0" in r.stdout and "rc1" not in r.stdout
    # the installed version is announced once (codex-dev finding: two lines in two formats)
    assert r.stdout.count("Installiert") == 1 and "Installierte Version:" not in r.stdout
    assert "Neue Version: LPIC-3 Trainer " in r.stdout
    build = (root / "opt" / "app" / "BUILD").read_text()
    assert "release=v99.0.0" in build and "dirty=false" in build
    # installed_at is the moment the files went live, after staging, backup and venv build
    installed_at = re.search(r"^installed_at=(.+)$", build, re.M).group(1)
    assert datetime.fromisoformat(installed_at).timestamp() > staged + 1
    r = cli(env2, "--version")
    assert r.returncode == 0 and r.stdout.startswith("LPIC-3 Trainer ")
    assert "release v99.0.0" in r.stdout and "commit " in r.stdout and "installiert " in r.stdout
    # already up to date: no change, no systemctl call
    before = stub_log(env)
    r = cli(env2, "--upgrade")
    assert r.returncode == 0 and "Bereits aktuell" in r.stdout, r.stdout + r.stderr
    assert stub_log(env) == before
    # development installation with the release's version number: hint, no replacement
    build_file = root / "opt" / "app" / "BUILD"
    original = build_file.read_text()
    build_file.write_text(
        re.sub(r"^version=.*$", "version=99.0.0", original, flags=re.M)
        .replace("release=v99.0.0", "release=")
        .replace("dirty=false", "dirty=true")
        + "branch=feat/x\n"
    )
    before = stub_log(env)
    r = cli(env2, "--upgrade")
    assert r.returncode == 0 and "Entwicklungsstand" in r.stdout, r.stdout + r.stderr
    assert "Bereits aktuell" not in r.stdout and "--source" in r.stdout
    assert stub_log(env) == before and build_file.read_text() != original
    build_file.write_text(original)
    # unreachable remote: exit 1, installation untouched
    r = cli({**env, "LPIC3_UPGRADE_REMOTE": str(remote) + "-missing"}, "--upgrade")
    assert r.returncode == 1 and "unverändert" in r.stderr and "--source" in r.stderr
    assert "release=v99.0.0" in (root / "opt" / "app" / "BUILD").read_text()


def test_04_rollback_refuses_unknown_schema_and_restores_backup(env):
    """Found on a real Debian 12 install: after a rollback the old code crashed on a newer
    schema. The rollback must refuse without the pre-upgrade backup and succeed with it."""
    import sqlite3

    root = Path(env["_root"])
    db = root / "var" / "lpic3-trainer.db"
    backup = sorted((root / "var" / "backups").glob("lpic3-trainer-backup-*.tar.gz"))[-1]
    conn = sqlite3.connect(db)
    conn.execute("UPDATE alembic_version SET version_num = '9999'")  # pretend: newer schema
    conn.commit()
    conn.close()
    r = cli(env, "rollback")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "Schema 9999" in r.stderr and "--restore" in r.stderr and backup.name in r.stderr
    assert (root / "opt" / "app.previous").is_dir(), "nothing may change when refusing"
    assert not (root / "opt" / "app.failed").exists()

    r = cli(env, "rollback", "--restore", str(backup))
    assert r.returncode == 0, r.stdout + r.stderr
    assert (root / "opt" / "app.failed").is_dir() and not (root / "opt" / "app.previous").exists()
    assert (root / "opt" / "app" / "pyproject.toml").is_file()
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] != "9999"
    conn.close()
    assert list((root / "var").glob("lpic3-trainer.before-restore-*.db")), "safety copy"


def test_05_status_and_version(env):
    r = cli(env, "status")
    assert r.returncode == 0 and "Schema:" in r.stdout
    r = cli(env, "version")
    assert r.returncode == 0 and r.stdout.startswith("LPIC-3 Trainer ") and "commit " in r.stdout


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
