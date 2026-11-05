"""Ownership and mode of the configuration directory after install.

Found during the real installation inside a Debian 12 container: the config directory
was created root:root 0750, so the service user could not read the environment file
and ``runuser -u lpic3 lpic3ctl content-sync`` failed. os.chown needs root, hence the
calls are recorded instead of executed.
"""

import os
import pwd

from app import cli


def test_chown_service_files_grants_group_access_to_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "etc"
    config_dir.mkdir(mode=0o700)
    env_file = config_dir / "lpic3-trainer.env"
    env_file.write_text("LPIC3_PORT=8000\n")
    env_file.chmod(0o600)
    data_dir = tmp_path / "var"
    data_dir.mkdir()
    (data_dir / "lpic3-trainer.db").write_bytes(b"")

    calls: list[tuple[str, int, int]] = []
    monkeypatch.setattr(cli, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(cli, "ENV_FILE", env_file)
    monkeypatch.setenv("LPIC3_DATA_DIR", str(data_dir))
    monkeypatch.setattr(
        pwd, "getpwnam", lambda name: pwd.struct_passwd((name, "x", 4321, 4322, "", "/", ""))
    )
    monkeypatch.setattr(os, "chown", lambda p, uid, gid: calls.append((str(p), uid, gid)))

    cli._chown_service_files()

    assert (str(config_dir), 0, 4322) in calls, "config dir must be group-owned by the service"
    assert (str(env_file), 0, 4322) in calls
    assert oct(config_dir.stat().st_mode)[-3:] == "750"
    assert oct(env_file.stat().st_mode)[-3:] == "640"
    # data directory and database belong to the service user
    assert (str(data_dir), 4321, 4322) in calls
    assert (str(data_dir / "lpic3-trainer.db"), 4321, 4322) in calls


def test_tar_extract_falls_back_without_filter_argument(tmp_path, monkeypatch):
    """Debian 12 (Python 3.11.2) has no ``filter`` argument on TarFile.extract."""
    import tarfile

    payload = tmp_path / "lpic3-trainer.db"
    payload.write_bytes(b"db")
    archive = tmp_path / "a.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(payload, arcname="lpic3-trainer.db")

    original = tarfile.TarFile.extract

    def old_extract(self, member, path="", set_attrs=True, *, numeric_owner=False, **kw):
        if "filter" in kw:
            raise TypeError("TarFile.extract() got an unexpected keyword argument 'filter'")
        return original(self, member, path, set_attrs, numeric_owner=numeric_owner)

    monkeypatch.setattr(tarfile.TarFile, "extract", old_extract)
    dest = tmp_path / "out"
    dest.mkdir()
    with tarfile.open(archive, "r:gz") as tar:
        cli._tar_extract(tar, "lpic3-trainer.db", str(dest))
    assert (dest / "lpic3-trainer.db").read_bytes() == b"db"


def test_service_in_restart_loop_counts_as_active(monkeypatch):
    monkeypatch.setattr(cli, "has_systemd", lambda: True)
    states = iter(["activating", "active", "inactive", "failed"])

    class Result:
        def __init__(self, out):
            self.stdout = out

    monkeypatch.setattr(cli, "systemctl", lambda *a, **k: Result(next(states) + "\n"))
    assert cli.service_active() is True  # activating
    assert cli.service_active() is True  # active
    assert cli.service_active() is False  # inactive
    assert cli.service_active() is False  # failed


def test_unreadable_config_does_not_crash(tmp_path, monkeypatch):
    env_file = tmp_path / "lpic3-trainer.env"
    env_file.write_text("LPIC3_PORT=1\n")
    real_is_file = type(env_file).is_file

    def denied(self):
        if self == env_file:
            raise PermissionError(13, "Permission denied", str(self))
        return real_is_file(self)

    monkeypatch.setattr(type(env_file), "is_file", denied)
    monkeypatch.setattr(cli, "CONFIG_UNREADABLE", False)
    assert cli.load_env_file(env_file) == {}
    assert cli.CONFIG_UNREADABLE is True


def test_code_and_db_revisions(tmp_path):
    from app.config import PROJECT_DIR

    known = cli._code_revisions(PROJECT_DIR)
    assert {"0001", "0005"} <= known
    import sqlite3

    db = tmp_path / "x.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE alembic_version (version_num TEXT)")
    conn.execute("INSERT INTO alembic_version VALUES ('0005')")
    conn.commit()
    conn.close()
    assert cli._db_revision(db) == "0005"
    assert cli._db_revision(tmp_path / "missing.db") is None
