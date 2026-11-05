"""Regression tests for P1-3: restore must never compete with a running server.

A real uvicorn server is started as a subprocess (not managed by systemd). The restore
has to be refused while it runs; after the server is stopped the restore must succeed,
the restored data must survive a restart, and the integrity check must run.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from tests.conftest import PROJECT_DIR


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def env(tmp_path):
    port = _free_port()
    return {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
        "LPIC3_DATA_DIR": str(tmp_path / "data"),
        "LPIC3_PORT": str(port),
        "LPIC3_HOST": "127.0.0.1",
        "LPIC3_LOG_LEVEL": "warning",
        "_port": str(port),
        "_tmp": str(tmp_path),
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
        timeout=300,
    )


class Server:
    def __init__(self, env):
        self.env = env
        self.proc = None

    def start(self):
        clean = {k: v for k, v in self.env.items() if not k.startswith("_")}
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "app.cli", "serve"],
            env=clean,
            cwd=PROJECT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        base = f"http://127.0.0.1:{self.env['_port']}"
        for _ in range(120):
            try:
                urllib.request.urlopen(base + "/health", timeout=1)
                return base
            except Exception:
                if self.proc.poll() is not None:
                    raise RuntimeError("server exited") from None
                time.sleep(0.25)
        raise RuntimeError("server did not start")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(timeout=15)
        self.proc = None


def _register(base: str, username: str) -> int:
    data = f"username={username}&password=geheim123&password2=geheim123".encode()
    req = urllib.request.Request(base + "/register", data=data, method="POST")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        return opener.open(req, timeout=10).status
    except urllib.error.HTTPError as exc:
        return exc.code


def _users(env) -> str:
    return cli(env, "user", "list").stdout


def test_restore_is_refused_while_a_server_runs_and_keeps_data(env):
    assert cli(env, "content-sync").returncode == 0  # P2-1: creates the data directory itself
    server = Server(env)
    try:
        base = server.start()
        assert _register(base, "before") == 303
        assert cli(env, "backup", "--to", env["_tmp"] + "/bk").returncode == 0
        archive = next(Path(env["_tmp"], "bk").glob("*.tar.gz"))
        assert _register(base, "after") == 303
        r = cli(env, "restore", str(archive), "--yes")
        assert r.returncode == 2, r.stdout + r.stderr
        assert "läuft noch ein Server" in r.stderr
        # nothing was touched: the server still serves both users from the live database
        assert _register(base, "after") == 400  # username taken -> data intact
        assert not list(Path(env["LPIC3_DATA_DIR"]).glob("*.before-restore-*"))
    finally:
        server.stop()
    listing = _users(env)
    assert "before" in listing and "after" in listing


def test_restore_after_stop_survives_restart(env):
    assert cli(env, "content-sync").returncode == 0
    server = Server(env)
    try:
        base = server.start()
        assert _register(base, "keepme") == 303
        assert cli(env, "backup", "--to", env["_tmp"] + "/bk").returncode == 0
        archive = next(Path(env["_tmp"], "bk").glob("*.tar.gz"))
        assert _register(base, "loseme") == 303
    finally:
        server.stop()
    r = cli(env, "restore", str(archive), "--yes")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "wiederhergestellt und geprüft" in r.stdout
    assert list(Path(env["LPIC3_DATA_DIR"]).glob("*.before-restore-*")), "safety copy missing"
    listing = _users(env)
    assert "keepme" in listing and "loseme" not in listing
    # the restored state is what a freshly started server serves, also after another restart
    for _ in range(2):
        server = Server(env)
        try:
            base = server.start()
            assert _register(base, "keepme") == 400  # exists in the restored database
            assert _register(base, "loseme") == 303  # free again
        finally:
            server.stop()
        listing = _users(env)
        assert "keepme" in listing and "loseme" in listing
        # remove loseme again for the second round
        import sqlite3

        conn = sqlite3.connect(Path(env["LPIC3_DATA_DIR"]) / "lpic3-trainer.db")
        conn.execute("DELETE FROM users WHERE username = 'loseme'")
        conn.commit()
        conn.close()


def test_restore_rejects_corrupt_archive(env):
    assert cli(env, "content-sync").returncode == 0
    bad = Path(env["_tmp"]) / "bad.tar.gz"
    import tarfile

    with tarfile.open(bad, "w:gz") as tar:
        p = Path(env["_tmp"]) / "lpic3-trainer.db"
        p.write_bytes(b"this is not a database")
        tar.add(p, arcname="lpic3-trainer.db")
    r = cli(env, "restore", str(bad), "--yes")
    assert r.returncode != 0
    assert (
        "Sicherheitskopie" in r.stderr
        or "Integrit" in r.stderr
        or "file is not a database" in (r.stderr + r.stdout)
    )


def test_commands_report_missing_prerequisites(env):
    r = cli(env, "backup")
    assert r.returncode == 1 and "nicht gefunden" in r.stderr
    r = cli(env, "restore", env["_tmp"] + "/missing.tar.gz", "--yes")
    assert r.returncode == 1 and "nicht gefunden" in r.stderr
    r = cli(env, "user", "set-role", "nobody", "admin")
    assert r.returncode == 1
