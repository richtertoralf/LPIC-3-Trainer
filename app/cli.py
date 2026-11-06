"""lpic3ctl: install, operate and administer the LPIC-3 Trainer.

Only the standard library is imported at module level so that ``python3 -m app.cli install``
works on a fresh system before the virtual environment exists.
"""

from __future__ import annotations

import argparse
import getpass
import os
import pwd
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from app import __version__

INSTALL_DIR = Path(os.environ.get("LPIC3_INSTALL_DIR", "/opt/lpic3-trainer"))
CONFIG_DIR = Path(os.environ.get("LPIC3_CONFIG_DIR", "/etc/lpic3-trainer"))
DEFAULT_DATA_DIR = Path(os.environ.get("LPIC3_DATA_DIR", "/var/lib/lpic3-trainer"))
ENV_FILE = CONFIG_DIR / "lpic3-trainer.env"
SERVICE_NAME = "lpic3-trainer"
SERVICE_USER = "lpic3"
SYSTEMD_DIR = Path(os.environ.get("LPIC3_SYSTEMD_DIR", "/etc/systemd/system"))
UNIT_PATH = SYSTEMD_DIR / f"{SERVICE_NAME}.service"
BIN_LINK = Path(os.environ.get("LPIC3_BIN_DIR", "/usr/local/bin")) / "lpic3ctl"
APP_DIR = INSTALL_DIR / "app"
PREVIOUS_DIR = INSTALL_DIR / "app.previous"
STAGING_DIR = INSTALL_DIR / "app.new"
STAGING_VENV = INSTALL_DIR / "venv.new"
VENV_DIR = INSTALL_DIR / "venv"
BUILD_FILE = APP_DIR / "BUILD"
SOURCE_DIR = Path(__file__).resolve().parent.parent
PRODUCT = "LPIC-3 Trainer"
# Upgrade source: the newest stable tag vX.Y.Z of this repository (RICHTER.PROJECTS ADR-002).
DEFAULT_REMOTE_URL = "https://github.com/richtertoralf/LPIC-3-Trainer.git"
STABLE_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

# Exit codes as in RICHTER.PROJECTS ADR-002: 0 success (also "already up to date" or a
# deliberately stopped service), 1 technical error (also "not installed"), 2 invalid
# parameters or configuration.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


class CliError(Exception):
    def __init__(self, message: str, code: int = EXIT_ERROR):
        super().__init__(message)
        self.code = code


def say(msg: str) -> None:
    # flush: keep our lines in order with the output of child processes (pip, content-sync)
    # when stdout is a pipe or a log file
    print(msg, flush=True)


def warn(msg: str) -> None:
    print(f"Warnung: {msg}", file=sys.stderr, flush=True)


CONFIG_UNREADABLE = False


def load_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    """Load LPIC3_* variables from the configuration file without overriding the environment."""
    global CONFIG_UNREADABLE
    values: dict[str, str] = {}
    try:
        if not path.is_file():
            return values
        text = path.read_text(encoding="utf-8")
    except PermissionError:
        # The file is 0640 root:lpic3 on purpose; a normal user may still run --help etc.
        CONFIG_UNREADABLE = True
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
        if key.startswith("LPIC3_") and key not in os.environ:
            os.environ[key] = value
    return values


def require_root() -> None:
    # LPIC3_UNPRIVILEGED_TEST=1 lets the automated tests exercise install/upgrade/uninstall
    # with stubbed system commands; never set it on a real system.
    if os.geteuid() != 0 and os.environ.get("LPIC3_UNPRIVILEGED_TEST") != "1":
        raise CliError("Dieser Befehl benötigt Root-Rechte (sudo).", EXIT_USAGE)


def run(
    cmd: list[str], check: bool = True, capture: bool = False, **kwargs
) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, capture_output=capture, **kwargs)


def has_systemd() -> bool:
    return shutil.which("systemctl") is not None and Path("/run/systemd/system").is_dir()


def systemctl(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return run(["systemctl", *args], check=check, capture=True)


def service_state() -> str:
    # Without our unit file (Docker, foreground server, test tree) systemd has nothing to
    # report about the trainer, so do not ask about a unit that may belong to another
    # installation on the same host.
    if not has_systemd() or not UNIT_PATH.exists():
        return "unknown"
    return systemctl("is-active", SERVICE_NAME, check=False).stdout.strip() or "unknown"


def service_active() -> bool:
    # "activating" is a service in a restart loop (e.g. after a failed start); it holds or
    # will hold the database open, so it must be stopped like an active one.
    return service_state() in ("active", "activating", "reloading")


# ----------------------------------------------------------------- application


def _settings():
    from app.config import get_settings

    return get_settings()


def cmd_serve(args) -> int:
    import uvicorn

    settings = _settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _migrate_and_sync(quiet=False)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    return EXIT_OK


def _migrate_and_sync(quiet: bool = True) -> None:
    from app.config import get_settings
    from app.content import sync_bundled_content
    from app.db import session_scope
    from app.migrate import upgrade_database

    upgrade_database()
    with session_scope() as db:
        results = sync_bundled_content(db, get_settings().content_dir)
    if not quiet:
        for r in results:
            if r.warnings:
                say(f"  {r.kind}: {', '.join(r.warnings)}")
            else:
                say(f"  {r.kind}: {r.created} neu, {r.updated} aktualisiert")


def cmd_migrate(args) -> int:
    from app.migrate import current_revision, upgrade_database

    upgrade_database()
    say(f"Datenbankschema: {current_revision()}")
    return EXIT_OK


def cmd_content_sync(args) -> int:
    say("Mitgelieferte Inhalte werden importiert ...")
    _migrate_and_sync(quiet=False)
    return EXIT_OK


def cmd_import(args) -> int:
    from app.content import ContentError, import_path
    from app.db import session_scope
    from app.migrate import upgrade_database

    upgrade_database()
    code = EXIT_OK
    for raw in args.files:
        path = Path(raw)
        try:
            with session_scope() as db:
                result = import_path(
                    db,
                    path,
                    bundled=False,
                    source=args.source,
                    source_url=args.source_url,
                    exam_code=args.exam_code,
                    exam_version=args.exam_version,
                    rights=args.rights,
                )
            say(f"{path.name}: {result.created} neu, {result.updated} aktualisiert ({result.kind})")
            for warning in result.warnings:
                warn(f"mögliche Dublette: {warning}")
        except (ContentError, FileNotFoundError) as exc:
            code = EXIT_ERROR
            errors = getattr(exc, "errors", [str(exc)])
            print(f"{path.name}: abgelehnt", file=sys.stderr)
            for e in errors[:50]:
                print(f"  - {e}", file=sys.stderr)
    return code


def cmd_validate(args) -> int:
    from app.content import ContentError, load_json, validate

    code = EXIT_OK
    for raw in args.files:
        path = Path(raw)
        try:
            errors = validate(load_json(path))
        except ContentError as exc:
            errors = exc.errors
        if errors:
            code = EXIT_ERROR
            print(f"{path.name}: {len(errors)} Fehler", file=sys.stderr)
            for e in errors[:50]:
                print(f"  - {e}", file=sys.stderr)
        else:
            say(f"{path.name}: gültig")
    return code


# ----------------------------------------------------------------------- users


def cmd_user(args) -> int:
    from sqlalchemy import select

    from app.db import session_scope
    from app.migrate import upgrade_database
    from app.models import ROLES, STATUS_ACTIVE, User
    from app.security import delete_user_sessions, hash_password, password_error

    upgrade_database()
    with session_scope() as db:
        if args.user_command == "list":
            for u in db.execute(select(User).order_by(User.username)).scalars():
                say(f"{u.username:24} {u.role:11} {u.status:9} {u.created_at:%Y-%m-%d}")
            return EXIT_OK
        if args.user_command == "create":
            if db.execute(select(User).where(User.username == args.username)).scalar_one_or_none():
                raise CliError(f"Benutzer {args.username} existiert bereits.")
            password = args.password or getpass.getpass("Passwort: ")
            if problem := password_error(password):
                raise CliError(problem)
            if args.role not in ROLES:
                raise CliError(f"Rolle muss eine von {', '.join(ROLES)} sein.", EXIT_USAGE)
            db.add(
                User(
                    username=args.username.lower(),
                    display_name=args.display_name or "",
                    password_hash=hash_password(password),
                    role=args.role,
                    status=STATUS_ACTIVE,
                )
            )
            say(f"Benutzer {args.username} ({args.role}) angelegt.")
            return EXIT_OK
        user = db.execute(select(User).where(User.username == args.username)).scalar_one_or_none()
        if user is None:
            raise CliError(f"Benutzer {args.username} nicht gefunden.", EXIT_ERROR)
        if args.user_command == "set-role":
            if args.role not in ROLES:
                raise CliError(f"Rolle muss eine von {', '.join(ROLES)} sein.", EXIT_USAGE)
            user.role = args.role
            say(f"{user.username} hat jetzt die Rolle {args.role}.")
        elif args.user_command == "set-password":
            password = args.password or getpass.getpass("Neues Passwort: ")
            if problem := password_error(password):
                raise CliError(problem)
            user.password_hash = hash_password(password)
            delete_user_sessions(db, user.id)
            say(f"Passwort von {user.username} geändert.")
        elif args.user_command == "activate":
            user.status = STATUS_ACTIVE
            say(f"{user.username} ist aktiv.")
        elif args.user_command == "disable":
            user.status = "disabled"
            delete_user_sessions(db, user.id)
            say(f"{user.username} ist deaktiviert.")
    return EXIT_OK


# ------------------------------------------------------------- backup/restore


def _backup_db_copy(db_path: Path, target: Path) -> None:
    import sqlite3

    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def cmd_backup(args) -> int:
    settings = _settings()
    db_path = settings.db_path
    if not db_path.is_file():
        raise CliError(f"Datenbank {db_path} nicht gefunden.", EXIT_ERROR)
    target_dir = Path(args.to) if args.to else settings.data_dir / "backups"
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = target_dir / f"lpic3-trainer-backup-{stamp}.tar.gz"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_db = Path(tmp) / "lpic3-trainer.db"
        _backup_db_copy(db_path, tmp_db)
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(tmp_db, arcname="lpic3-trainer.db")
            try:
                has_env = ENV_FILE.is_file()
            except PermissionError:
                has_env = False
                warn(f"{ENV_FILE} nicht lesbar; Sicherung ohne Konfiguration (sudo verwenden).")
            if has_env:
                tar.add(ENV_FILE, arcname="lpic3-trainer.env")
            meta = Path(tmp) / "VERSION"
            meta.write_text(f"{__version__}\n")
            tar.add(meta, arcname="VERSION")
    os.chmod(archive, 0o600)
    say(f"Sicherung erstellt: {archive}")
    if args.keep:
        backups = sorted(target_dir.glob("lpic3-trainer-backup-*.tar.gz"))
        for old in backups[: max(0, len(backups) - args.keep)]:
            old.unlink()
            say(f"Alte Sicherung entfernt: {old.name}")
    return EXIT_OK


def _tar_extract(tar: tarfile.TarFile, member: str, dest: str) -> None:
    """Extract one member safely. The ``filter`` argument exists from Python 3.11.4/3.12;
    Debian 12 ships 3.11.2, where the call used to fail with TypeError."""
    try:
        tar.extract(member, dest, filter="data")
    except TypeError:
        info = tar.getmember(member)
        if info.name != Path(info.name).name or not info.isfile():
            raise CliError(f"Unerwarteter Archivinhalt: {info.name}") from None
        tar.extract(member, dest)


def _ensure_no_foreign_server(settings) -> bool:
    """Stop the systemd service if it runs; refuse when another server holds the database.

    Returns True when the systemd service was stopped and has to be started again."""
    if service_active():
        systemctl("stop", SERVICE_NAME)
        return True
    if _http_health(settings.host, settings.port).startswith("ok"):
        # A server not managed by systemd (Docker, foreground) keeps the old database file
        # open and would silently write into the deleted file after the restore.
        raise CliError(
            f"Unter http://{settings.host}:{settings.port}/ läuft noch ein Server, der nicht "
            "über systemd verwaltet wird. Bitte zuerst stoppen (Docker: docker compose stop) "
            "und die Wiederherstellung danach ausführen.",
            EXIT_USAGE,
        )
    return False


def _swap_database(archive: Path, db_path: Path, with_config: bool = False) -> None:
    """Replace the database file (and optionally the config) with the archive content.

    Keeps a safety copy of the current database next to it. Runs no migration."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        if "lpic3-trainer.db" not in names:
            raise CliError("Das Archiv enthält keine Datenbank.")
        with tempfile.TemporaryDirectory() as tmp:
            _tar_extract(tar, "lpic3-trainer.db", tmp)
            if db_path.exists():
                safety = db_path.with_name(
                    f"lpic3-trainer.before-restore-{datetime.now():%Y%m%d-%H%M%S}.db"
                )
                _backup_db_copy(db_path, safety)
                say(f"Vorherige Datenbank vor dem Restore gesichert: {safety}")
            for suffix in ("", "-wal", "-shm"):
                p = Path(str(db_path) + suffix)
                if p.exists():
                    p.unlink()
            shutil.move(str(Path(tmp) / "lpic3-trainer.db"), db_path)
            if with_config and "lpic3-trainer.env" in names:
                _tar_extract(tar, "lpic3-trainer.env", tmp)
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(Path(tmp) / "lpic3-trainer.env", ENV_FILE)
                os.chmod(ENV_FILE, 0o640)
                say(f"Konfiguration wiederhergestellt: {ENV_FILE}")
    _chown_service_files()


def _db_revision(db_path: Path) -> str | None:
    import sqlite3

    if not db_path.is_file():
        return None
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def _code_revisions(app_dir: Path) -> set[str]:
    """Revision ids known to the code in app_dir (without importing it)."""
    import re

    found: set[str] = set()
    for path in (app_dir / "migrations" / "versions").glob("*.py"):
        m = re.search(r'^revision\s*[:=]\s*["\']([^"\']+)["\']', path.read_text(), re.M)
        if m:
            found.add(m.group(1))
    return found


def cmd_restore(args) -> int:
    archive = Path(args.archive)
    if not archive.is_file():
        raise CliError(f"Archiv {archive} nicht gefunden.", EXIT_ERROR)
    settings = _settings()
    db_path = settings.db_path
    if not args.yes:
        answer = input(f"Datenbank {db_path} durch {archive.name} ersetzen? [ja/NEIN] ")
        if answer.strip().lower() not in ("ja", "j", "yes", "y"):
            say("Abgebrochen.")
            return EXIT_USAGE
    was_active = _ensure_no_foreign_server(settings)
    _swap_database(archive, db_path, with_config=args.with_config)
    from app.db import reset_engine
    from app.migrate import upgrade_database

    reset_engine()
    upgrade_database()
    integrity = _integrity_check(db_path)
    if integrity != "ok":
        raise CliError(
            f"Integritätsprüfung der wiederhergestellten Datenbank fehlgeschlagen: {integrity}. "
            "Die vorherige Datenbank liegt als Sicherheitskopie im Datenverzeichnis."
        )
    say(f"Datenbank wiederhergestellt und geprüft: {db_path}")
    if was_active:
        systemctl("start", SERVICE_NAME)
        health = _wait_for_health(settings.host, settings.port)
        say(f"Dienst gestartet, Health-Check: {health}")
        if not health.startswith("ok"):
            return EXIT_ERROR
    return EXIT_OK


def _integrity_check(db_path: Path) -> str:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return str(conn.execute("PRAGMA integrity_check").fetchone()[0])
    finally:
        conn.close()


def _wait_for_health(host: str, port: int, attempts: int = 20) -> str:
    import time

    result = "nicht erreichbar"
    for _ in range(attempts):
        result = _http_health(host, port)
        if result.startswith("ok"):
            return result
        time.sleep(0.5)
    return result


# ---------------------------------------------------------------- installation


def _check_prerequisites() -> list[str]:
    problems = []
    if sys.version_info < (3, 11):  # noqa: UP036 - message for old systems
        problems.append(
            f"Python 3.11 oder neuer wird benötigt (gefunden {sys.version.split()[0]})."
        )
    try:
        import ensurepip  # noqa: F401
        import venv  # noqa: F401
    except ImportError:
        problems.append("Das Modul venv fehlt. Bitte python3-venv installieren.")
    if not has_systemd():
        problems.append("systemd wurde nicht gefunden. Installation nur mit systemd möglich.")
    return problems


def _ensure_user() -> None:
    try:
        pwd.getpwnam(SERVICE_USER)
    except KeyError:
        run(
            [
                "useradd",
                "--system",
                "--home-dir",
                str(DEFAULT_DATA_DIR),
                "--shell",
                "/usr/sbin/nologin",
                "--no-create-home",
                SERVICE_USER,
            ]
        )
        say(f"Systembenutzer {SERVICE_USER} angelegt.")


def _chown_service_files() -> None:
    try:
        info = pwd.getpwnam(SERVICE_USER)
    except KeyError:
        return
    try:
        _chown_service_files_as(info)
    except PermissionError:
        # Only root may hand files to the service user. Happens in the unprivileged test run
        # on a host that has a real lpic3 account; a real installation always runs as root.
        warn("Eigentümer nicht gesetzt (keine Root-Rechte).")


def _chown_service_files_as(info) -> None:
    data_dir = Path(os.environ.get("LPIC3_DATA_DIR", str(DEFAULT_DATA_DIR)))
    for root in (data_dir,):
        if root.exists():
            for p in [root, *root.rglob("*")]:
                os.chown(p, info.pw_uid, info.pw_gid)
    # The service user must be able to traverse the config directory, otherwise
    # ``runuser -u lpic3 lpic3ctl content-sync`` cannot read the environment file.
    if CONFIG_DIR.exists():
        os.chown(CONFIG_DIR, 0, info.pw_gid)
        os.chmod(CONFIG_DIR, 0o750)
    if ENV_FILE.exists():
        os.chown(ENV_FILE, 0, info.pw_gid)
        os.chmod(ENV_FILE, 0o640)


def _copy_source(source: Path, target: Path) -> None:
    if target.exists():
        if PREVIOUS_DIR.exists():
            shutil.rmtree(PREVIOUS_DIR)
        shutil.move(str(target), str(PREVIOUS_DIR))
    _copy_tree(source, target)


def _copy_tree(source: Path, target: Path) -> None:
    """Copy a source checkout to ``target`` and record the build information there."""
    ignore = shutil.ignore_patterns(
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "data",
        "backups",
        ".pytest_cache",
        ".ruff_cache",
        "test-results",
        "*.db",
        "*.db-*",
        "node_modules",
        ".env",
    )
    shutil.copytree(source, target, ignore=ignore, symlinks=False)
    try:
        describe = run(
            ["git", "-C", str(source), "describe", "--tags", "--always", "--dirty"],
            check=False,
            capture=True,
        )
        if describe.returncode == 0:
            (target / "GIT_VERSION").write_text(describe.stdout.strip() + "\n")
    except FileNotFoundError:
        pass
    _write_build_info(source, target)


def _git(source: Path, *args: str) -> str:
    """Output of a git command in ``source`` or an empty string (no git, no repository)."""
    try:
        result = run(["git", "-C", str(source), *args], check=False, capture=True)
    except FileNotFoundError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _version_in(app_dir: Path) -> str:
    init = app_dir / "app" / "__init__.py"
    if init.is_file():
        for line in init.read_text().splitlines():
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"')
    return "unbekannt"


def _release_tag(source: Path) -> str:
    """Release tag of the checked-out commit: the highest stable ``vX.Y.Z`` tag pointing at HEAD
    (the one ``--upgrade`` selects), otherwise whatever ``git describe`` reports. ``describe``
    alone prefers annotated tags, so a commit carrying several tags could be recorded under a
    tag other than the installed release."""
    tags = [t for t in _git(source, "tag", "--points-at", "HEAD").split() if STABLE_TAG_RE.match(t)]
    if tags:
        return max(tags, key=_parse_version)
    return _git(source, "describe", "--tags", "--exact-match")


def _write_build_info(source: Path, target: Path) -> None:
    """Write ``BUILD`` (version, commit, branch, release, dirty, source, time) into ``target``.

    Every path that copies program files goes through here, so ``--version`` and ``--status``
    can report the installed software state offline (ADR-002, section 4.1).
    """
    branch = _git(source, "rev-parse", "--abbrev-ref", "HEAD")
    info = {
        "version": _version_in(target),
        "commit": _git(source, "rev-parse", "HEAD") or "unbekannt",
        "branch": branch if branch and branch != "HEAD" else "",
        "release": _release_tag(source),
        "dirty": "true" if _git(source, "status", "--porcelain") else "false",
        "source": str(source),
        "installed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    (target / "BUILD").write_text("".join(f"{k}={v}\n" for k, v in info.items()))


def _build_info() -> dict[str, str]:
    """Build information of the installation (empty when not installed or pre-BUILD)."""
    info: dict[str, str] = {}
    if BUILD_FILE.is_file():
        for line in BUILD_FILE.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep:
                info[key.strip()] = value.strip()
    return info


def _parse_version(text: str) -> tuple[int, ...] | None:
    """``v0.0.3`` / ``0.0.3`` -> (0, 0, 3); anything else -> None."""
    match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)$", text.strip())
    return tuple(int(x) for x in match.groups()) if match else None


def _version_line() -> str:
    """One line in the RICHTER.PROJECTS format, without network, venv or running service."""
    if not APP_DIR.exists():
        return (
            f"{PRODUCT} {__version__} (nicht installiert; dieses lpic3ctl läuft aus {SOURCE_DIR})"
        )
    info = _build_info()
    version = info.get("version") or _installed_version()
    parts = [f"commit {info['commit'][:7] if info.get('commit') else 'unbekannt'}"]
    if info.get("dirty") == "true":
        parts[0] += ", dirty"
    if info.get("release"):
        parts.append(f"release {info['release']}")
    elif info.get("branch"):
        parts.append(f"branch {info['branch']}")
    else:
        parts.append("branch unbekannt")
    parts.append(f"installiert {info.get('installed_at') or 'unbekannt'}")
    return f"{PRODUCT} {version} ({', '.join(parts)})"


def remote_url() -> str:
    """Upgrade remote: LPIC3_UPGRADE_REMOTE (environment or the central env file, for
    mirrors and tests), otherwise the project repository. Read at call time, after
    ``load_env_file()``."""
    return os.environ.get("LPIC3_UPGRADE_REMOTE") or DEFAULT_REMOTE_URL


def _latest_stable_tag(remote: str | None = None) -> tuple[str, tuple[int, ...]]:
    """Newest tag ``vX.Y.Z`` of the remote. Pre-releases (``v1.0.0-rc1``) are ignored."""
    tag, parsed, _ = _latest_stable_release(remote)
    return tag, parsed


def _latest_stable_release(remote: str | None = None) -> tuple[str, tuple[int, ...], str]:
    """Newest stable tag of the remote with the commit it points to (peeled for annotated tags,
    empty when the remote does not report it)."""
    remote = remote or remote_url()
    try:
        result = run(
            ["git", "ls-remote", "--tags", remote],
            check=False,
            capture=True,
            timeout=60,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except FileNotFoundError:
        raise CliError("git ist nicht installiert; Upgrade mit --source PFAD.") from None
    except subprocess.TimeoutExpired:
        raise CliError(
            "Keine Antwort von GitHub; Installation unverändert. "
            "Netz prüfen oder Upgrade mit --source PFAD."
        ) from None
    if result.returncode != 0:
        raise CliError(
            "Kein Zugriff auf GitHub; Installation unverändert. "
            "Netz prüfen oder Upgrade mit --source PFAD."
        )
    tags: dict[str, tuple[int, ...]] = {}
    commits: dict[str, str] = {}
    for line in result.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        if "refs/tags/" not in ref:
            continue
        tag = ref.split("refs/tags/")[-1].strip()
        peeled = tag.endswith("^{}")
        tag = tag.removesuffix("^{}")
        parsed = _parse_version(tag) if STABLE_TAG_RE.match(tag) else None
        if not parsed:
            continue
        tags[tag] = parsed
        # "<sha> refs/tags/vX^{}" is the commit of an annotated tag; a lightweight tag has
        # only the plain line, whose sha already is the commit.
        if peeled or tag not in commits:
            commits[tag] = sha.strip()
    if not tags:
        raise CliError("Kein stabiles Release (Tag vX.Y.Z) gefunden; Installation unverändert.")
    tag = max(tags, key=tags.get)
    return tag, tags[tag], commits.get(tag, "")


def _development_state(info: dict[str, str], release_commit: str = "") -> str:
    """Why an installation is a development state rather than the release with the same
    version number; empty when it is the release (installed from the tag, or the very commit
    the tag points to, without local changes)."""
    reasons = []
    commit = info.get("commit", "")
    if info.get("dirty") == "true":
        reasons.append("lokale Änderungen (dirty)")
    if not info.get("release"):
        if info.get("branch"):
            reasons.append(f"Branch {info['branch']}")
        if release_commit and commit and commit != release_commit:
            reasons.append(f"Commit {commit[:7]} statt {release_commit[:7]}")
        elif not release_commit and not reasons:
            reasons.append(f"Commit {commit[:7] or 'unbekannt'} ohne Release-Tag")
    return ", ".join(reasons)


def _create_venv() -> None:
    script = APP_DIR / "deploy" / "create-venv.sh"
    run(["bash", str(script), str(VENV_DIR), str(APP_DIR)])


def _write_env_file(force: bool = False) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o750)
    if ENV_FILE.exists() and not force:
        say(f"Konfiguration {ENV_FILE} bleibt erhalten.")
        return
    template = APP_DIR / "deploy" / "lpic3-trainer.env.example"
    shutil.copy2(template, ENV_FILE)
    os.chmod(ENV_FILE, 0o640)
    say(f"Konfiguration angelegt: {ENV_FILE}")


def _install_unit() -> None:
    unit = (APP_DIR / "deploy" / "lpic3-trainer.service").read_text()
    UNIT_PATH.write_text(unit)
    systemctl("daemon-reload")


def _run_as_service_user(args: list[str]) -> None:
    env = {k: v for k, v in os.environ.items() if k.startswith("LPIC3_") or k in ("PATH", "LANG")}
    if os.geteuid() != 0:
        run(args, env=env)
        return
    run(["runuser", "-u", SERVICE_USER, "--", *args], env=env)


def cmd_install(args) -> int:
    require_root()
    problems = _check_prerequisites()
    if problems:
        for p in problems:
            print(f"Fehlende Voraussetzung: {p}", file=sys.stderr)
        return EXIT_ERROR
    source = Path(args.source).resolve() if args.source else SOURCE_DIR
    if not (source / "pyproject.toml").is_file():
        raise CliError(f"{source} enthält keinen LPIC-3-Trainer-Quellcode.", EXIT_USAGE)
    existing = APP_DIR.exists()
    if existing and not args.force:
        say(
            f"Es gibt bereits eine Installation unter {INSTALL_DIR}. Nutze 'lpic3ctl upgrade' "
            "oder 'install --force'."
        )
        return EXIT_USAGE
    say(f"Installation nach {INSTALL_DIR} ...")
    _ensure_user()
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    _copy_source(source, APP_DIR)
    _create_venv()
    _write_env_file()
    env = load_env_file()
    # values already present in the environment take precedence over the file
    env = {**env, **{k: v for k, v in os.environ.items() if k.startswith("LPIC3_")}}
    data_dir = Path(env.get("LPIC3_DATA_DIR", str(DEFAULT_DATA_DIR)))
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o750)
    (data_dir / "backups").mkdir(exist_ok=True, mode=0o750)
    _chown_service_files()
    port = env.get("LPIC3_PORT", "8000")
    host = env.get("LPIC3_HOST", "127.0.0.1")
    if not existing and _port_in_use(host, int(port)):
        warn(
            f"Port {port} ist bereits belegt. Passe LPIC3_PORT in {ENV_FILE} an, "
            "bevor du den Dienst startest."
        )
    say("Datenbank wird eingerichtet und Inhalte werden importiert ...")
    _run_as_service_user([str(VENV_DIR / "bin" / "lpic3ctl"), "content-sync"])
    _install_unit()
    if BIN_LINK.is_symlink() or BIN_LINK.exists():
        BIN_LINK.unlink()
    BIN_LINK.symlink_to(VENV_DIR / "bin" / "lpic3ctl")
    systemctl("enable", SERVICE_NAME)
    if not args.no_start:
        systemctl("restart", SERVICE_NAME)
        say(f"Dienst {SERVICE_NAME} gestartet auf http://{host}:{port}/")
    say(
        "Installation abgeschlossen. Das erste registrierte Konto erhält Administratorrechte, "
        "alternativ: lpic3ctl user create <name> --role admin"
    )
    return EXIT_OK


def _port_in_use(host: str, port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            return s.connect_ex((host if host != "0.0.0.0" else "127.0.0.1", port)) == 0
        except OSError:
            return False


def _installed_version() -> str:
    marker = APP_DIR / "GIT_VERSION"
    if marker.is_file():
        return marker.read_text().strip()
    init = APP_DIR / "app" / "__init__.py"
    if init.is_file():
        for line in init.read_text().splitlines():
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"')
    return "nicht installiert"


def cmd_upgrade(args) -> int:
    require_root()
    if not APP_DIR.exists():
        raise CliError("Keine Installation gefunden. Bitte zuerst 'lpic3ctl install' ausführen.")
    load_env_file()
    tmp: str | None = None
    if args.source:
        source = Path(args.source).resolve()
        if source == APP_DIR:
            raise CliError(
                "Bitte das Upgrade aus einem frischen Quellcode-Checkout starten "
                "(z. B. git clone + git checkout vX.Y.Z), nicht aus dem installierten Verzeichnis.",
                EXIT_USAGE,
            )
    else:
        # Standard way (ADR-002): the newest stable release tag of the repository.
        tag, latest, release_commit = _latest_stable_release()
        info = _build_info()
        installed_text = info.get("release") or info.get("version") or _installed_version()
        installed = _parse_version(installed_text)
        say(f"Installiert: {installed_text}, neuestes stabiles Release: {tag}")
        if installed is not None and installed == latest:
            development = _development_state(info, release_commit)
            if development:
                # Same version number, but not the release: say so and leave it alone.
                say(
                    f"Hinweis: Die Installation trägt die Versionsnummer von {tag}, ist aber ein "
                    f"Entwicklungsstand ({development}). Sie wird nicht ungefragt ersetzt.\n"
                    f"Release installieren: git clone {remote_url()} && cd LPIC-3-Trainer && "
                    f'git checkout {tag} && sudo lpic3ctl --upgrade --source "$PWD"'
                )
                return EXIT_OK
            say("Bereits aktuell. Keine Änderung, kein Neustart.")
            return EXIT_OK
        if installed is not None and installed > latest:
            say(
                "Der installierte Stand ist neuer als das neueste Release; kein Downgrade. "
                "Ein anderer Stand lässt sich mit --source PFAD installieren."
            )
            return EXIT_OK
        tmp = tempfile.mkdtemp(prefix="lpic3-upgrade-")
        source = Path(tmp) / "src"
        clone = run(
            ["git", "clone", "--quiet", "--depth", "1", "--branch", tag, remote_url(), str(source)],
            check=False,
            capture=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        if clone.returncode != 0:
            shutil.rmtree(tmp, ignore_errors=True)
            raise CliError(
                f"Release {tag} konnte nicht geladen werden; Installation unverändert.\n"
                f"{clone.stderr.strip()}"
            )
    if not (source / "pyproject.toml").is_file():
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
        raise CliError(f"{source} enthält keinen LPIC-3-Trainer-Quellcode.", EXIT_USAGE)
    try:
        return _perform_upgrade(source, args)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def _probe_new_version(stage: Path) -> None:
    """Build the new version next to the running one and check it before any service stop.

    The probe venv is a throwaway: it proves that the dependencies resolve, the package
    imports and the operator's existing configuration is accepted by the new code.
    """
    if STAGING_VENV.exists():
        shutil.rmtree(STAGING_VENV)
    run(["bash", str(stage / "deploy" / "create-venv.sh"), str(STAGING_VENV), str(stage)])
    env = {k: v for k, v in os.environ.items() if k.startswith("LPIC3_") or k in ("PATH", "LANG")}
    env["LPIC3_QUIET_MIGRATIONS"] = "1"
    probe = run(
        [
            str(STAGING_VENV / "bin" / "python"),
            "-c",
            "import app.main\nfrom app.config import Settings\nSettings()",
        ],
        check=False,
        capture=True,
        env=env,
        cwd=str(stage),
    )
    shutil.rmtree(STAGING_VENV, ignore_errors=True)
    if probe.returncode != 0:
        detail = probe.stderr.strip().splitlines()
        last = detail[-1] if detail else "unbekannter Fehler"
        config_error = "ValueError" in last and "LPIC3_" in last
        raise CliError(
            "Die neue Version wurde nicht übernommen, der Dienst läuft unverändert weiter: "
            + (
                f"die vorhandene Konfiguration passt nicht zur neuen Version ({last})"
                if config_error
                else f"Start-Probe fehlgeschlagen ({last})"
            ),
            EXIT_USAGE if config_error else EXIT_ERROR,
        )


def _perform_upgrade(source: Path, args) -> int:
    say(f"Installierte Version: {_installed_version()}")
    # 1. Stage and check the new version while the service keeps running.
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    say("Neue Version wird neben der laufenden aufgebaut und geprüft ...")
    try:
        _copy_tree(source, STAGING_DIR)
        _probe_new_version(STAGING_DIR)
    except Exception:
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
        raise
    # 2. Backup, then swap with the service stopped; the systemd state is restored exactly.
    say("Sicherung vor dem Upgrade ...")
    backup_args = argparse.Namespace(to=None, keep=None)
    settings = _settings()
    if settings.db_path.is_file():
        cmd_backup(backup_args)
    was_active = service_active()
    if was_active:
        systemctl("stop", SERVICE_NAME)
    try:
        if PREVIOUS_DIR.exists():
            shutil.rmtree(PREVIOUS_DIR)
        shutil.move(str(APP_DIR), str(PREVIOUS_DIR))
        shutil.move(str(STAGING_DIR), str(APP_DIR))
        _create_venv()
        _write_env_file()
        _chown_service_files()
        _run_as_service_user([str(VENV_DIR / "bin" / "lpic3ctl"), "content-sync"])
        _install_unit()
    except Exception as exc:
        warn(f"Upgrade fehlgeschlagen: {exc}")
        if PREVIOUS_DIR.exists():
            warn("Vorherige Version wird wiederhergestellt ...")
            if APP_DIR.exists():
                shutil.rmtree(APP_DIR)
            shutil.move(str(PREVIOUS_DIR), str(APP_DIR))
            _create_venv()
        if was_active:
            systemctl("start", SERVICE_NAME, check=False)
        return EXIT_ERROR
    if was_active and not args.no_start:
        systemctl("restart", SERVICE_NAME)
    elif not was_active:
        say("Der Dienst war gestoppt und bleibt gestoppt.")
    say(f"Upgrade abgeschlossen. Neue Version: {_installed_version()}")
    say(f"Vorherige Programmdateien liegen unter {PREVIOUS_DIR} ('lpic3ctl rollback').")
    return EXIT_OK


def cmd_rollback(args) -> int:
    require_root()
    if not PREVIOUS_DIR.exists():
        raise CliError("Keine vorherige Version vorhanden.", EXIT_ERROR)
    load_env_file()
    settings = _settings()
    db_path = settings.db_path
    archive = Path(args.restore).resolve() if args.restore else None
    if archive and not archive.is_file():
        raise CliError(f"Archiv {archive} nicht gefunden.", EXIT_ERROR)
    # The previous code must know the database schema, otherwise the service would
    # crash at start (Alembic: "Can't locate revision"). Checked before touching anything.
    db_rev = _db_revision(db_path)
    known = _code_revisions(PREVIOUS_DIR)
    if db_rev and known and db_rev not in known and archive is None:
        backups = sorted((settings.data_dir / "backups").glob("lpic3-trainer-backup-*.tar.gz"))
        hint = f"z. B. {backups[-1]}" if backups else "Sicherung von vor dem Upgrade"
        raise CliError(
            f"Die Datenbank hat Schema {db_rev}, das die vorherige Version nicht kennt. "
            "Rollback nur zusammen mit der Sicherung von vor dem Upgrade:\n"
            f"  lpic3ctl rollback --restore <Archiv>   ({hint})",
            EXIT_USAGE,
        )
    if archive is not None:
        with tarfile.open(archive, "r:gz") as tar:
            if "lpic3-trainer.db" not in tar.getnames():
                raise CliError("Das Archiv enthält keine Datenbank.")
    was_active = _ensure_no_foreign_server(settings)
    current = INSTALL_DIR / "app.failed"
    if current.exists():
        shutil.rmtree(current)
    shutil.move(str(APP_DIR), str(current))
    shutil.move(str(PREVIOUS_DIR), str(APP_DIR))
    _create_venv()
    _install_unit()
    say(
        f"Programmdateien zurückgesetzt auf {_installed_version()}. "
        f"Die fehlgeschlagene Version liegt unter {current}."
    )
    if archive is not None:
        _swap_database(archive, db_path)
        integrity = _integrity_check(db_path)
        if integrity != "ok":
            raise CliError(
                f"Integritätsprüfung der wiederhergestellten Datenbank fehlgeschlagen: {integrity}."
            )
        restored_rev = _db_revision(db_path)
        if known and restored_rev and restored_rev not in known:
            raise CliError(
                f"Die Sicherung hat Schema {restored_rev}, das die vorherige Version nicht kennt."
            )
        say(f"Datenbank aus {archive.name} wiederhergestellt (Schema {restored_rev}).")
    else:
        say("Hinweis: Die Datenbank wurde nicht verändert.")
    if was_active:
        systemctl("start", SERVICE_NAME)
        health = _wait_for_health(settings.host, settings.port)
        say(f"Dienst gestartet, Health-Check: {health}")
        if not health.startswith("ok"):
            return EXIT_ERROR
    return EXIT_OK


def cmd_version(args) -> int:
    say(_version_line())
    if getattr(args, "remote", False):
        try:
            tag, _ = _latest_stable_tag()
            say(f"Neuestes stabiles Release: {tag}")
        except CliError as exc:
            say(f"Neuestes stabiles Release: nicht abrufbar ({exc})")
    return EXIT_OK


def _lan_addresses(ip_output: str | None = None) -> list[str]:
    """Global IPv4 addresses of the host's own interfaces (LAN, VPN), without the virtual
    bridges, veths and taps of containers and VMs."""
    return [address for _, address in _host_addresses(ip_output)]


def _host_addresses(ip_output: str | None = None) -> list[tuple[str, str]]:
    """``(interface, IPv4 address)`` pairs from ``ip -o -4 addr show scope global``."""
    if ip_output is None:
        try:
            ip_output = run(
                ["ip", "-o", "-4", "addr", "show", "scope", "global"], check=False, capture=True
            ).stdout
        except FileNotFoundError:
            return []
    skip = (
        "docker", "br-", "virbr", "lxdbr", "lxcbr", "incusbr", "podman", "cni", "flannel",
        "veth", "vnet", "tap",
    )  # fmt: skip
    addresses = []
    for line in ip_output.splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[2] != "inet":
            continue
        iface, address = fields[1], fields[3].split("/")[0]
        if iface.startswith(skip):
            continue
        addresses.append((iface, address))
    return addresses


def _access_urls(host: str, port: int) -> list[str]:
    """Configured addresses with port: the loopback address and, when bound to all interfaces,
    every LAN and VPN address of the host, each labelled with its interface. They are read
    from the configuration and the interfaces, not probed; reachability depends on firewall
    and network."""
    if host in ("0.0.0.0", "::", ""):
        return [f"http://127.0.0.1:{port}/ (lo)"] + [
            f"http://{address}:{port}/ ({iface})" for iface, address in _host_addresses()
        ]
    shown = f"[{host}]" if ":" in host else host
    return [f"http://{shown}:{port}/"]


def cmd_status(args) -> int:
    """Read-only state. Exit 0 also for a deliberately stopped service, 1 for a technical
    error (unit failed, active but not answering, not installed), 2 for invalid configuration."""
    load_env_file()
    if not APP_DIR.exists():
        say(f"{PRODUCT}: nicht installiert ({INSTALL_DIR} fehlt), siehe docs/installation.md")
        return EXIT_ERROR
    code = EXIT_OK
    say(f"Version:       {_version_line()}")
    state = "nicht installiert"
    if has_systemd() and UNIT_PATH.exists():
        state = systemctl("is-active", SERVICE_NAME, check=False).stdout.strip() or "unknown"
        enabled = systemctl("is-enabled", SERVICE_NAME, check=False).stdout.strip() or "unknown"
        say(f"Dienst:        {state}")
        say(f"Autostart:     {enabled}")
        if state == "failed":
            code = EXIT_ERROR
    else:
        say("Dienst:        nicht installiert")
    if CONFIG_UNREADABLE:
        # Without the configuration every further line would rest on defaults (wrong
        # database path, wrong port) and mislead. Say what is missing and stop here.
        say(f"Konfiguration: {ENV_FILE} (ohne Root-Rechte nicht lesbar)")
        say("Hinweis:       Bitte sudo lpic3ctl --status verwenden.")
        return code
    say(f"Konfiguration: {ENV_FILE}" + ("" if ENV_FILE.is_file() else " (fehlt)"))
    try:
        settings = _settings()
    except ValueError as exc:
        say(f"Fehler:        ungültige Konfiguration: {exc}")
        return EXIT_USAGE
    say(
        f"Datenbank:     {settings.db_path} "
        f"({'vorhanden' if settings.db_path.exists() else 'fehlt'})"
    )
    try:
        from app.db import db_health

        info = db_health()
        say(f"Schema:        {info['schema_version']} (journal {info['journal_mode']})")
    except PermissionError:
        say("Schema:        ohne Root-Rechte nicht lesbar")
        say("Hinweis:       Bitte sudo lpic3ctl --status verwenden.")
    except Exception as exc:
        say(f"Schema:        nicht lesbar ({exc.__class__.__name__})")
    health = _http_health(settings.host, settings.port)
    if state in ("active", "activating", "reloading") and not health.startswith("ok"):
        # Found in the container test: right after a (re)start the unit is "active" while
        # the application still runs migrations and the content import. Retry briefly
        # before calling it an error.
        import time

        for _ in range(5):
            time.sleep(2)
            health = _http_health(settings.host, settings.port)
            if health.startswith("ok"):
                break
    say(f"Health-Check:  {health}")
    if state in ("active", "activating", "reloading") and not health.startswith("ok"):
        say("Fehler:        Dienst aktiv, aber der Health-Endpunkt antwortet nicht.")
        code = EXIT_ERROR
    running = _running_version(health)
    installed = _build_info().get("version")
    if running and installed and running != installed:
        say(f"Hinweis:       laufend {running}, installiert {installed}: Neustart nötig.")
    for url in _access_urls(settings.host, settings.port):
        say(f"Adresse:       {url}")
    if settings.host in ("0.0.0.0", "::", ""):
        say("               (konfigurierte Adressen; Erreichbarkeit aus dem Netz nicht geprüft)")
    return code


def _running_version(health: str) -> str:
    match = re.search(r"Version ([^)]+)\)", health)
    return match.group(1) if match else ""


def _http_health(host: str, port: int) -> str:
    import json
    import urllib.request

    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:  # noqa: S310 - local URL
            data = json.loads(resp.read())
            return f"{data.get('status')} (Version {data.get('version')})"
    except Exception as exc:
        return f"nicht erreichbar ({exc.__class__.__name__})"


def _service_cmd(action: str) -> int:
    require_root()
    if not UNIT_PATH.exists():
        raise CliError("Der Dienst ist nicht installiert.", EXIT_ERROR)
    result = systemctl(action, SERVICE_NAME, check=False)
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        return EXIT_ERROR
    say(f"Dienst {SERVICE_NAME}: {action} ausgeführt.")
    return EXIT_OK


def cmd_start(args) -> int:
    return _service_cmd("start")


def cmd_stop(args) -> int:
    return _service_cmd("stop")


def cmd_restart(args) -> int:
    return _service_cmd("restart")


def cmd_logs(args) -> int:
    if shutil.which("journalctl") is None:
        raise CliError("journalctl nicht gefunden.", EXIT_ERROR)
    cmd = ["journalctl", "-u", SERVICE_NAME, "-n", str(args.lines), "--no-pager"]
    if args.follow:
        cmd.append("-f")
    return subprocess.call(cmd)


def cmd_check(args) -> int:
    load_env_file()
    ok = True

    def report(label: str, good: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and good
        say(f"[{'OK' if good else '!!'}] {label}{(': ' + detail) if detail else ''}")

    report("Python", sys.version_info >= (3, 11), sys.version.split()[0])
    report(
        "Konfiguration",
        not CONFIG_UNREADABLE and ENV_FILE.is_file(),
        f"{ENV_FILE}" + (" (nicht lesbar, Root-Rechte nötig)" if CONFIG_UNREADABLE else ""),
    )
    try:
        settings = _settings()
    except ValueError as exc:
        report("Konfigurationswerte", False, str(exc))
        return EXIT_ERROR
    report(
        "Passwortrichtlinie",
        True,
        f"{settings.password_min_length} bis {settings.password_max_length} Zeichen",
    )
    report("Datenverzeichnis", settings.data_dir.is_dir(), str(settings.data_dir))
    if settings.data_dir.is_dir():
        report("Datenverzeichnis beschreibbar", os.access(settings.data_dir, os.W_OK))
    report("Datenbank", settings.db_path.is_file(), str(settings.db_path))
    if settings.db_path.is_file():
        try:
            from app.migrate import current_revision, head_revision

            cur, head = current_revision(), head_revision()
            report("Schema aktuell", cur == head, f"{cur} / {head}")
        except Exception as exc:
            report("Schema lesbar", False, str(exc))
    from app.content import ContentError, content_files, load_json, validate

    files = content_files(settings.content_dir)
    bad = []
    for path in files:
        try:
            errors = validate(load_json(path))
        except ContentError as exc:
            errors = exc.errors
        if errors:
            bad.append(path.name)
    report(
        "Inhaltsdateien gültig",
        not bad,
        f"{len(files)} Dateien" + (f", fehlerhaft: {', '.join(bad)}" if bad else ""),
    )
    if has_systemd():
        report("systemd-Unit", UNIT_PATH.exists(), str(UNIT_PATH))
        if UNIT_PATH.exists():
            report("Dienst aktiv", service_active())
    report(
        "Health-Endpunkt",
        _http_health(settings.host, settings.port).startswith("ok"),
        _http_health(settings.host, settings.port),
    )
    if settings.host not in ("127.0.0.1", "localhost", "::1") and not settings.secure_cookies:
        say(
            "[..] Hinweis: Öffentliche Bindung ohne LPIC3_SECURE_COOKIES=true. "
            "Nur hinter einem HTTPS-Reverse-Proxy betreiben."
        )
    return EXIT_OK if ok else EXIT_ERROR


def cmd_uninstall(args) -> int:
    require_root()
    if has_systemd() and UNIT_PATH.exists():
        systemctl("disable", "--now", SERVICE_NAME, check=False)
        UNIT_PATH.unlink()
        systemctl("daemon-reload")
        say("Dienst entfernt.")
    if BIN_LINK.is_symlink():
        BIN_LINK.unlink()
    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR)
        say(f"Programmdateien unter {INSTALL_DIR} entfernt.")
    say(f"Konfiguration ({CONFIG_DIR}) und Daten ({DEFAULT_DATA_DIR}) bleiben erhalten.")
    return EXIT_OK


def cmd_purge(args) -> int:
    require_root()
    load_env_file()
    data_dir = Path(os.environ.get("LPIC3_DATA_DIR", str(DEFAULT_DATA_DIR)))
    if not args.yes:
        answer = input(
            f"Alle Daten unter {data_dir} und {CONFIG_DIR} endgültig löschen? Tippe 'löschen': "
        )
        if answer.strip() != "löschen":
            say("Abgebrochen.")
            return EXIT_USAGE
    cmd_uninstall(args)
    for path in (data_dir, CONFIG_DIR):
        if path.exists() and path not in (Path("/"), Path("/var/lib"), Path("/etc")):
            shutil.rmtree(path)
            say(f"{path} entfernt.")
    try:
        pwd.getpwnam(SERVICE_USER)
        run(["userdel", SERVICE_USER], check=False)
        say(f"Systembenutzer {SERVICE_USER} entfernt.")
    except KeyError:
        pass
    return EXIT_OK


# ---------------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lpic3ctl",
        description="LPIC-3 Trainer installieren, betreiben und verwalten.",
        epilog=(
            "Verwaltung nach RICHTER.PROJECTS-Standard (Langoptionen, gleichwertig zu den "
            "Unterbefehlen):\n"
            "  lpic3ctl --version                  installierte Version und Herkunft (offline)\n"
            "  lpic3ctl --status                   Betriebszustand, Exit 0/1/2\n"
            "  sudo lpic3ctl --upgrade             neuestes stabiles Release installieren\n"
            "  sudo lpic3ctl --upgrade --source P  aus einem lokalen Checkout installieren\n"
            "  sudo lpic3ctl --uninstall           entfernen, Konfiguration und Daten bleiben\n"
            "  sudo lpic3ctl --uninstall --purge   zusätzlich Konfiguration und Daten entfernen\n"
            "  zusätzlich: --check, --restart"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("install", help="Anwendung installieren (Root)")
    p.add_argument("--source", help="Quellverzeichnis (Standard: dieses Checkout)")
    p.add_argument("--force", action="store_true", help="bestehende Installation überschreiben")
    p.add_argument("--no-start", action="store_true", help="Dienst nicht starten")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser(
        "upgrade", help="auf das neueste stabile Release aktualisieren (Root); --source: lokal"
    )
    p.add_argument("--source", help="Quellverzeichnis mit der neuen Version statt GitHub-Release")
    p.add_argument("--no-start", action="store_true")
    p.set_defaults(func=cmd_upgrade)

    p = sub.add_parser("rollback", help="vorherige Programmversion wiederherstellen (Root)")
    p.add_argument(
        "--restore",
        metavar="ARCHIV",
        help="zusätzlich die Datenbank aus dieser Sicherung (von vor dem Upgrade) einspielen",
    )
    p.set_defaults(func=cmd_rollback)
    p = sub.add_parser("version", help="installierte Version und Herkunft anzeigen (offline)")
    p.add_argument("--remote", action="store_true", help="zusätzlich das neueste Release abfragen")
    p.set_defaults(func=cmd_version)
    sub.add_parser("status", help="Dienststatus und Systemzustand").set_defaults(func=cmd_status)
    sub.add_parser("start", help="Dienst starten").set_defaults(func=cmd_start)
    sub.add_parser("stop", help="Dienst stoppen").set_defaults(func=cmd_stop)
    sub.add_parser("restart", help="Dienst neu starten").set_defaults(func=cmd_restart)

    p = sub.add_parser("logs", help="Dienstprotokolle anzeigen")
    p.add_argument("-n", "--lines", type=int, default=100)
    p.add_argument("-f", "--follow", action="store_true")
    p.set_defaults(func=cmd_logs)

    p = sub.add_parser("backup", help="Datenbank und Konfiguration sichern")
    p.add_argument("--to", help="Zielverzeichnis (Standard: <Datenverzeichnis>/backups)")
    p.add_argument("--keep", type=int, help="nur die letzten N Sicherungen behalten")
    p.set_defaults(func=cmd_backup)

    p = sub.add_parser("restore", help="Sicherung wiederherstellen")
    p.add_argument("archive")
    p.add_argument(
        "--with-config", action="store_true", help="auch die Konfiguration wiederherstellen"
    )
    p.add_argument("--yes", action="store_true", help="ohne Rückfrage")
    p.set_defaults(func=cmd_restore)

    sub.add_parser("check", help="Installation und Konfiguration prüfen").set_defaults(
        func=cmd_check
    )
    sub.add_parser("uninstall", help="Anwendung entfernen, Daten behalten (Root)").set_defaults(
        func=cmd_uninstall
    )
    p = sub.add_parser("purge", help="Anwendung mit allen Daten entfernen (Root)")
    p.add_argument("--yes", action="store_true", help="ohne Rückfrage löschen")
    p.set_defaults(func=cmd_purge)

    sub.add_parser("serve", help="Anwendung im Vordergrund starten").set_defaults(func=cmd_serve)
    sub.add_parser("migrate", help="Datenbankmigrationen ausführen").set_defaults(func=cmd_migrate)
    sub.add_parser("content-sync", help="mitgelieferte Inhalte importieren").set_defaults(
        func=cmd_content_sync
    )

    p = sub.add_parser(
        "import",
        help="Inhaltsdateien (JSON) importieren; Fragen bleiben bis zur Freigabe unveröffentlicht",
    )
    p.add_argument("files", nargs="+")
    p.add_argument(
        "--source", default=None, help="Quellenbezeichnung, z. B. 'ExamTopics 04.11.2026'"
    )
    p.add_argument("--exam-version", default=None, help="Prüfungsgeneration, z. B. 3.0")
    p.add_argument("--exam-code", default=None, help="Prüfungsnummer, z. B. 305-300")
    p.add_argument("--source-url", default=None, help="Original-URL der Quelle")
    p.add_argument(
        "--rights",
        choices=["cleared", "unknown", "unverified"],
        default=None,
        help="Rechtestatus der Quelle",
    )
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("validate", help="Inhaltsdateien prüfen, ohne zu importieren")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("user", help="Benutzer verwalten")
    us = p.add_subparsers(dest="user_command", required=True)
    us.add_parser("list")
    c = us.add_parser("create")
    c.add_argument("username")
    c.add_argument("--role", default="learner", help="admin, supervisor oder learner")
    c.add_argument("--display-name", default="")
    c.add_argument("--password", help="(unsicher: besser interaktiv eingeben)")
    r = us.add_parser("set-role")
    r.add_argument("username")
    r.add_argument("role")
    sp = us.add_parser("set-password")
    sp.add_argument("username")
    sp.add_argument("--password")
    us.add_parser("activate").add_argument("username")
    us.add_parser("disable").add_argument("username")
    p.set_defaults(func=cmd_user)
    return parser


def _restore_data_ownership() -> None:
    """Hand files back to the service user after root ran a command that touched the DB.

    ``lpic3ctl user create`` or ``migrate`` run as root while the service is stopped would
    otherwise leave root-owned ``-wal``/``-shm`` files and the service could not write.
    """
    if os.geteuid() != 0 or os.environ.get("LPIC3_UNPRIVILEGED_TEST") == "1":
        return
    try:
        _chown_service_files()
    except OSError as exc:  # pragma: no cover - best effort
        warn(f"Dateirechte konnten nicht gesetzt werden: {exc}")


# Long options of the RICHTER.PROJECTS standard (ADR-002) mapped onto the existing
# subcommands. ``--uninstall --purge`` becomes ``purge``; everything after the option is
# passed through unchanged, so ``--upgrade --source PFAD`` works as documented.
LONG_OPTIONS = {
    "--version": "version",
    "--status": "status",
    "--upgrade": "upgrade",
    "--uninstall": "uninstall",
    "--check": "check",
    "--restart": "restart",
}


def translate_argv(argv: list[str]) -> list[str]:
    if not argv or argv[0] not in LONG_OPTIONS:
        return argv
    rest = list(argv[1:])
    if argv[0] == "--uninstall" and "--purge" in rest:
        rest.remove("--purge")
        return ["purge", *rest]
    return [LONG_OPTIONS[argv[0]], *rest]


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    parser = build_parser()
    args = parser.parse_args(translate_argv(sys.argv[1:] if argv is None else list(argv)))
    if args.command not in ("serve", "migrate", "upgrade", "install", "content-sync", "import"):
        os.environ.setdefault("LPIC3_QUIET_MIGRATIONS", "1")
    try:
        result = args.func(args)
        _restore_data_ownership()
        return result
    except CliError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return exc.code
    except ValueError as exc:
        # ConfigError: invalid LPIC3_* value (exit 2). Other ValueErrors, e.g. an invalid
        # content file during content-sync, are ordinary errors (exit 1); seen in the
        # container test, where they were mislabelled as configuration errors.
        from app.config import ConfigError

        if isinstance(exc, ConfigError):
            print(f"Fehler: Ungültige Konfiguration: {exc}", file=sys.stderr)
            return EXIT_USAGE
        print(f"Fehler: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except subprocess.CalledProcessError as exc:
        print(f"Fehler: Befehl fehlgeschlagen: {' '.join(exc.cmd)}", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
