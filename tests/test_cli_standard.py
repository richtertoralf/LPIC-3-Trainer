"""lpic3ctl follows the RICHTER.PROJECTS administration standard (ADR-002):
long options as aliases, offline ``--version`` with build information, ``--status``
exit codes 0/1/2 with access URLs, newest stable release tag as upgrade source."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from app import __version__, cli
from tests.conftest import PROJECT_DIR


def run_cli(*args, env_extra=None):
    env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", **(env_extra or {})}
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=PROJECT_DIR,
        timeout=120,
    )


def test_long_options_map_onto_existing_subcommands():
    t = cli.translate_argv
    assert t(["--version"]) == ["version"]
    assert t(["--status"]) == ["status"]
    assert t(["--upgrade", "--source", "/x"]) == ["upgrade", "--source", "/x"]
    assert t(["--uninstall"]) == ["uninstall"]
    assert t(["--uninstall", "--purge", "--yes"]) == ["purge", "--yes"]
    assert t(["--check"]) == ["check"] and t(["--restart"]) == ["restart"]
    assert t(["backup", "--keep", "3"]) == ["backup", "--keep", "3"]
    assert t([]) == []


def test_help_lists_standard_options_and_bad_parameters_exit_2(tmp_path):
    r = run_cli("--help", env_extra={"LPIC3_INSTALL_DIR": str(tmp_path)})
    assert r.returncode == 0
    for option in ("--version", "--status", "--upgrade --source", "--uninstall --purge"):
        assert option in r.stdout
    assert run_cli("--bogus").returncode == 2
    r = run_cli("--upgrade", "--bogus", env_extra={"LPIC3_INSTALL_DIR": str(tmp_path)})
    assert r.returncode == 2


def test_version_offline_formats(tmp_path, monkeypatch):
    app_dir = tmp_path / "app"
    monkeypatch.setattr(cli, "APP_DIR", app_dir)
    monkeypatch.setattr(cli, "BUILD_FILE", app_dir / "BUILD")
    assert cli._version_line().startswith(f"LPIC-3 Trainer {__version__} (nicht installiert")
    app_dir.mkdir()
    (app_dir / "BUILD").write_text(
        "version=0.0.3\ncommit=0123456789abcdef\nbranch=main\nrelease=\ndirty=true\n"
        "source=/tmp/x\ninstalled_at=2026-11-05T10:00:00+01:00\n"
    )
    assert cli._version_line() == (
        "LPIC-3 Trainer 0.0.3 (commit 0123456, dirty, branch main, "
        "installiert 2026-11-05T10:00:00+01:00)"
    )
    (app_dir / "BUILD").write_text(
        "version=0.0.3\ncommit=0123456789abcdef\nbranch=\nrelease=v0.0.3\ndirty=false\n"
        "installed_at=2026-11-05T10:00:00+01:00\n"
    )
    assert "(commit 0123456, release v0.0.3, installiert" in cli._version_line()
    (app_dir / "BUILD").unlink()  # installation from before BUILD existed: nothing is guessed
    (app_dir / "GIT_VERSION").write_text("v0.0.2\n")
    assert cli._version_line() == (
        "LPIC-3 Trainer v0.0.2 (commit unbekannt, branch unbekannt, installiert unbekannt)"
    )
    # the subprocess form runs without network, venv or service
    r = run_cli("--version", env_extra={"LPIC3_INSTALL_DIR": str(tmp_path / "nowhere")})
    assert r.returncode == 0 and r.stdout.startswith("LPIC-3 Trainer ")


def test_newest_stable_tag_ignores_prereleases(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git = ["git", "-C", str(repo)]
    subprocess.run([*git, "init", "--quiet"], check=True)
    subprocess.run(
        [
            *git,
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@x",
            "commit",
            "--quiet",
            "--allow-empty",
            "-m",
            "init",
        ],
        check=True,
    )
    with pytest.raises(cli.CliError, match="Kein stabiles Release"):
        cli._latest_stable_tag(str(repo))
    for tag in ("v0.1.0", "v0.10.0", "v0.2.0", "v1.0.0-rc1", "v0.9.9", "snapshot"):
        subprocess.run([*git, "tag", tag], check=True)
    assert cli._latest_stable_tag(str(repo)) == ("v0.10.0", (0, 10, 0))
    with pytest.raises(cli.CliError, match="unverändert"):
        cli._latest_stable_tag(str(tmp_path / "missing"))
    assert cli._parse_version("v0.0.3") == (0, 0, 3) and cli._parse_version("0.0.3") == (0, 0, 3)
    assert cli._parse_version("v0.0.3-4-gabcdef") is None and cli._parse_version("main") is None


def test_build_release_is_the_highest_stable_tag_on_the_commit(tmp_path):
    """A commit may carry several tags (e.g. the real release tag and a later re-tag). BUILD
    records the highest stable one, which is the tag ``--upgrade`` installs; ``git describe``
    alone would prefer an annotated tag regardless of its version."""
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "__init__.py").write_text('__version__ = "1.0.0"\n')
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.org"]
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "commit", "--quiet", "-m", "init"], check=True)
    subprocess.run([*git, "tag", "-a", "v0.0.4", "-m", "annotated older release"], check=True)
    subprocess.run([*git, "tag", "v1.0.0"], check=True)
    subprocess.run([*git, "tag", "v1.1.0-rc1"], check=True)
    cli._write_build_info(repo, repo)
    build = (repo / "BUILD").read_text()
    assert "release=v1.0.0\n" in build and "version=1.0.0\n" in build, build

    subprocess.run([*git, "tag", "-d", "v0.0.4", "v1.0.0"], check=True, capture_output=True)
    cli._write_build_info(repo, repo)
    assert "release=v1.1.0-rc1\n" in (repo / "BUILD").read_text(), "fallback: git describe"


def test_upgrade_remote_comes_from_the_central_env_file(tmp_path, monkeypatch):
    """Found in the container test: the remote was read at import time, so a mirror set in
    /etc/lpic3-trainer/lpic3-trainer.env was ignored."""
    monkeypatch.delenv("LPIC3_UPGRADE_REMOTE", raising=False)
    assert cli.remote_url() == cli.DEFAULT_REMOTE_URL
    env_file = tmp_path / "lpic3-trainer.env"
    env_file.write_text("LPIC3_UPGRADE_REMOTE=/srv/mirror/lpic3.git\n")
    cli.load_env_file(env_file)
    assert cli.remote_url() == "/srv/mirror/lpic3.git"
    monkeypatch.setenv("LPIC3_UPGRADE_REMOTE", "/other.git")
    assert cli.remote_url() == "/other.git"


def test_invalid_content_file_is_not_reported_as_configuration_error(tmp_path):
    """Container test, failed-upgrade case: content-sync on a broken content file said
    'Ungültige Konfiguration'. Only LPIC3_* values are configuration errors (exit 2)."""
    content = tmp_path / "content"
    for sub in ("objectives", "vocabulary", "questions", "labs"):
        (content / sub).mkdir(parents=True)
    (content / "objectives" / "300.json").write_text("{ kaputt")
    env = {"LPIC3_DATA_DIR": str(tmp_path / "data"), "LPIC3_CONTENT_DIR": str(content)}
    r = run_cli("content-sync", env_extra=env)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "300.json" in r.stderr and "Ungültige Konfiguration" not in r.stderr
    r = run_cli("content-sync", env_extra={**env, "LPIC3_PASSWORD_MIN_LENGTH": "x"})
    assert r.returncode == 2 and "Ungültige Konfiguration" in r.stderr


def test_access_urls_skip_virtual_interfaces():
    sample = (
        "2: enp1s0    inet 10.77.0.108/24 metric 100 brd 10.77.0.255 scope global dynamic enp1s0\n"
        "4: wg0    inet 172.16.90.123/32 scope global wg0\n"
        "5: lxdbr0    inet 10.200.77.1/24 scope global lxdbr0\n"
        "6: docker0    inet 172.17.0.1/16 scope global docker0\n"
        "7: virbr0    inet 192.168.122.1/24 scope global virbr0\n"
    )
    assert cli._lan_addresses(sample) == ["10.77.0.108", "172.16.90.123"]
    assert cli._access_urls("127.0.0.1", 8000) == ["http://127.0.0.1:8000/"]
    assert cli._access_urls("192.168.1.20", 8080) == ["http://192.168.1.20:8080/"]
    assert cli._access_urls("0.0.0.0", 8000)[0] == "http://127.0.0.1:8000/"


@pytest.fixture
def fake_install(tmp_path):
    """A minimal installation tree with a stub systemctl whose is-active answer is STUB_STATE."""
    root = tmp_path
    (root / "opt" / "app").mkdir(parents=True)
    (root / "opt" / "app" / "BUILD").write_text(f"version={__version__}\ncommit=abc\n")
    (root / "systemd").mkdir()
    (root / "systemd" / "lpic3-trainer.service").write_text("[Unit]\n")
    (root / "etc").mkdir()
    (root / "etc" / "lpic3-trainer.env").write_text("LPIC3_PORT=18999\n")
    (root / "var").mkdir()
    stubs = root / "stubs"
    stubs.mkdir()
    stub = stubs / "systemctl"
    stub.write_text(
        '#!/bin/sh\ncase "$1" in is-active) echo "$STUB_STATE";; is-enabled) echo enabled;; esac\n'
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return {
        "PATH": f"{stubs}:{os.environ.get('PATH', '')}",
        "LPIC3_INSTALL_DIR": str(root / "opt"),
        "LPIC3_CONFIG_DIR": str(root / "etc"),
        "LPIC3_DATA_DIR": str(root / "var"),
        "LPIC3_SYSTEMD_DIR": str(root / "systemd"),
        "LPIC3_BIN_DIR": str(root / "bin"),
    }


def status(env, state):
    return run_cli("--status", env_extra={**env, "STUB_STATE": state})


def test_status_not_installed_is_exit_1(tmp_path):
    r = run_cli("--status", env_extra={"LPIC3_INSTALL_DIR": str(tmp_path / "none")})
    assert r.returncode == 1 and "nicht installiert" in r.stdout


@pytest.mark.skipif(not cli.has_systemd(), reason="needs a systemd host for the unit check")
def test_status_exit_codes_follow_adr_002(fake_install):
    r = status(fake_install, "inactive")
    assert r.returncode == 0, r.stdout + r.stderr  # deliberately stopped is not an error
    assert "Dienst:        inactive" in r.stdout and "Autostart:     enabled" in r.stdout
    assert "Adresse:       http://127.0.0.1:18999/" in r.stdout
    assert r.stdout.startswith("Version:       LPIC-3 Trainer ")
    r = status(fake_install, "failed")
    assert r.returncode == 1 and "failed" in r.stdout
    r = status(fake_install, "active")  # active but nothing answers on the port
    assert r.returncode == 1 and "antwortet nicht" in r.stdout
    bad = {**fake_install, "STUB_STATE": "active", "LPIC3_PASSWORD_MAX_LENGTH": "1"}
    r = run_cli("--status", env_extra=bad)
    assert r.returncode == 2 and "LPIC3_PASSWORD_MAX_LENGTH" in r.stdout


def test_status_shows_lan_urls_when_bound_to_all_interfaces(fake_install):
    Path(fake_install["LPIC3_CONFIG_DIR"], "lpic3-trainer.env").write_text(
        "LPIC3_PORT=18999\nLPIC3_HOST=0.0.0.0\n"
    )
    r = status(fake_install, "inactive")
    assert "Adresse:       http://127.0.0.1:18999/" in r.stdout
    assert r.stdout.count("Adresse:") == 1 + len(cli._lan_addresses())
