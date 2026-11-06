"""lpic3ctl: migrations, user management, backup, restore and check via subprocess."""

import os
import subprocess
import sys
import tarfile

import pytest

from tests.conftest import PROJECT_DIR


def run_cli(data_dir, *args, input_text=None):
    env = {
        "LPIC3_DATA_DIR": str(data_dir),
        # keep the test away from a real installation on the host (/etc, systemd unit)
        "LPIC3_CONFIG_DIR": os.path.join(str(data_dir), "etc"),
        "LPIC3_SYSTEMD_DIR": os.path.join(str(data_dir), "systemd"),
        "LPIC3_PORT": "18764",  # not the port of a real installation on the host
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
    }
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=PROJECT_DIR,
        input=input_text,
    )


@pytest.fixture
def fresh(tmp_path):
    r = run_cli(tmp_path, "content-sync")
    assert r.returncode == 0, r.stderr
    return tmp_path


def test_migrate_is_idempotent(fresh):
    from app.migrate import head_revision

    r = run_cli(fresh, "migrate")
    assert r.returncode == 0 and head_revision() in r.stdout
    assert (fresh / "lpic3-trainer.db").exists()


def test_user_commands(fresh):
    r = run_cli(fresh, "user", "create", "cliadmin", "--role", "admin", "--password", "geheim123")
    assert r.returncode == 0, r.stderr
    r = run_cli(fresh, "user", "create", "cliadmin", "--role", "admin", "--password", "geheim123")
    assert r.returncode == 1 and "existiert" in r.stderr
    r = run_cli(fresh, "user", "create", "weak", "--password", "123")
    assert r.returncode == 1
    r = run_cli(fresh, "user", "set-role", "cliadmin", "supervisor")
    assert r.returncode == 0
    r = run_cli(fresh, "user", "set-role", "nobody", "admin")
    assert r.returncode == 1
    r = run_cli(fresh, "user", "disable", "cliadmin")
    assert r.returncode == 0
    r = run_cli(fresh, "user", "list")
    assert "cliadmin" in r.stdout and "supervisor" in r.stdout and "disabled" in r.stdout


def test_backup_and_restore_roundtrip(fresh, tmp_path):
    run_cli(fresh, "user", "create", "before", "--password", "geheim123")
    backup_dir = tmp_path / "bk"
    r = run_cli(fresh, "backup", "--to", str(backup_dir))
    assert r.returncode == 0, r.stderr
    archives = list(backup_dir.glob("lpic3-trainer-backup-*.tar.gz"))
    assert len(archives) == 1
    with tarfile.open(archives[0]) as tar:
        names = tar.getnames()
    assert "lpic3-trainer.db" in names and "VERSION" in names
    assert oct(archives[0].stat().st_mode)[-3:] == "600"
    # change state after the backup
    run_cli(fresh, "user", "create", "after", "--password", "geheim123")
    assert "after" in run_cli(fresh, "user", "list").stdout
    r = run_cli(fresh, "restore", str(archives[0]), "--yes")
    assert r.returncode == 0, r.stderr
    listing = run_cli(fresh, "user", "list").stdout
    assert "before" in listing and "after" not in listing
    assert list(fresh.glob("lpic3-trainer.before-restore-*.db"))


def test_restore_requires_confirmation(fresh, tmp_path):
    r = run_cli(fresh, "backup", "--to", str(tmp_path / "b"))
    archive = next((tmp_path / "b").glob("*.tar.gz"))
    r = run_cli(fresh, "restore", str(archive), input_text="nein\n")
    assert r.returncode == 2 and "Abgebrochen" in r.stdout


def test_backup_keep_rotation(fresh, tmp_path):
    target = tmp_path / "rot"
    for _ in range(3):
        import time

        time.sleep(1.1)
        assert run_cli(fresh, "backup", "--to", str(target), "--keep", "2").returncode == 0
    assert len(list(target.glob("*.tar.gz"))) == 2


def test_check_reports_state(fresh):
    r = run_cli(fresh, "check")
    assert "Schema aktuell" in r.stdout and "Inhaltsdateien gültig" in r.stdout
    assert "[OK] Datenbank" in r.stdout


def test_version_and_help(fresh):
    r = run_cli(fresh, "--help")
    assert r.returncode == 0 and "backup" in r.stdout and "purge" in r.stdout
    r = run_cli(fresh, "backup", "--help")
    assert r.returncode == 0


def test_health_endpoint(client):
    data = client.get("/health").json()
    from app.migrate import head_revision

    assert data["status"] == "ok" and data["database"]["schema_version"] == head_revision()
    assert data["database"]["journal_mode"] == "wal"


def test_install_requires_root(fresh):
    r = run_cli(fresh, "install")
    assert r.returncode in (2, 3)
