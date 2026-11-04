"""lpic3ctl: install, operate and administer the LPIC-3 Trainer.

Only the standard library is imported at module level so that ``python3 -m app.cli install``
works on a fresh system before the virtual environment exists.
"""

from __future__ import annotations

import argparse
import getpass
import os
import pwd
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
VENV_DIR = INSTALL_DIR / "venv"
SOURCE_DIR = Path(__file__).resolve().parent.parent

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_MISSING = 3


class CliError(Exception):
    def __init__(self, message: str, code: int = EXIT_ERROR):
        super().__init__(message)
        self.code = code


def say(msg: str) -> None:
    print(msg)


def warn(msg: str) -> None:
    print(f"Warnung: {msg}", file=sys.stderr)


def load_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    """Load LPIC3_* variables from the configuration file without overriding the environment."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
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


def service_active() -> bool:
    if not has_systemd():
        return False
    return systemctl("is-active", SERVICE_NAME, check=False).stdout.strip() == "active"


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
                result = import_path(db, path, visibility=args.visibility, bundled=False)
            say(f"{path.name}: {result.created} neu, {result.updated} aktualisiert ({result.kind})")
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
    from app.security import MIN_PASSWORD_LENGTH, delete_user_sessions, hash_password

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
            if len(password) < MIN_PASSWORD_LENGTH:
                raise CliError(f"Das Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen haben.")
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
            raise CliError(f"Benutzer {args.username} nicht gefunden.", EXIT_MISSING)
        if args.user_command == "set-role":
            if args.role not in ROLES:
                raise CliError(f"Rolle muss eine von {', '.join(ROLES)} sein.", EXIT_USAGE)
            user.role = args.role
            say(f"{user.username} hat jetzt die Rolle {args.role}.")
        elif args.user_command == "set-password":
            password = args.password or getpass.getpass("Neues Passwort: ")
            if len(password) < MIN_PASSWORD_LENGTH:
                raise CliError(f"Das Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen haben.")
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
        raise CliError(f"Datenbank {db_path} nicht gefunden.", EXIT_MISSING)
    target_dir = Path(args.to) if args.to else settings.data_dir / "backups"
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = target_dir / f"lpic3-trainer-backup-{stamp}.tar.gz"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_db = Path(tmp) / "lpic3-trainer.db"
        _backup_db_copy(db_path, tmp_db)
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(tmp_db, arcname="lpic3-trainer.db")
            if ENV_FILE.is_file():
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


def cmd_restore(args) -> int:
    archive = Path(args.archive)
    if not archive.is_file():
        raise CliError(f"Archiv {archive} nicht gefunden.", EXIT_MISSING)
    settings = _settings()
    db_path = settings.db_path
    if not args.yes:
        answer = input(f"Datenbank {db_path} durch {archive.name} ersetzen? [ja/NEIN] ")
        if answer.strip().lower() not in ("ja", "j", "yes", "y"):
            say("Abgebrochen.")
            return EXIT_USAGE
    was_active = service_active()
    if was_active:
        systemctl("stop", SERVICE_NAME)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        if "lpic3-trainer.db" not in names:
            raise CliError("Das Archiv enthält keine Datenbank.")
        with tempfile.TemporaryDirectory() as tmp:
            tar.extract("lpic3-trainer.db", tmp, filter="data")
            if db_path.exists():
                safety = db_path.with_name(
                    f"lpic3-trainer.before-restore-{datetime.now():%Y%m%d-%H%M%S}.db"
                )
                _backup_db_copy(db_path, safety)
                say(f"Vorherige Datenbank gesichert: {safety}")
            for suffix in ("", "-wal", "-shm"):
                p = Path(str(db_path) + suffix)
                if p.exists():
                    p.unlink()
            shutil.move(str(Path(tmp) / "lpic3-trainer.db"), db_path)
            if args.with_config and "lpic3-trainer.env" in names:
                tar.extract("lpic3-trainer.env", tmp, filter="data")
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(Path(tmp) / "lpic3-trainer.env", ENV_FILE)
                os.chmod(ENV_FILE, 0o640)
                say(f"Konfiguration wiederhergestellt: {ENV_FILE}")
    _chown_service_files()
    from app.db import reset_engine
    from app.migrate import upgrade_database

    reset_engine()
    upgrade_database()
    say(f"Datenbank wiederhergestellt: {db_path}")
    if was_active:
        systemctl("start", SERVICE_NAME)
        say("Dienst gestartet.")
    return EXIT_OK


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
    data_dir = Path(os.environ.get("LPIC3_DATA_DIR", str(DEFAULT_DATA_DIR)))
    for root in (data_dir,):
        if root.exists():
            for p in [root, *root.rglob("*")]:
                os.chown(p, info.pw_uid, info.pw_gid)
    if ENV_FILE.exists():
        os.chown(ENV_FILE, 0, info.pw_gid)


def _copy_source(source: Path, target: Path) -> None:
    if target.exists():
        if PREVIOUS_DIR.exists():
            shutil.rmtree(PREVIOUS_DIR)
        shutil.move(str(target), str(PREVIOUS_DIR))
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
        return EXIT_MISSING
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
        raise CliError(
            "Keine Installation gefunden. Bitte zuerst 'lpic3ctl install' ausführen.", EXIT_MISSING
        )
    source = Path(args.source).resolve() if args.source else SOURCE_DIR
    if source == APP_DIR:
        raise CliError(
            "Bitte das Upgrade aus einem frischen Quellcode-Checkout starten "
            "(z. B. git clone + git checkout vX.Y.Z), nicht aus dem installierten Verzeichnis.",
            EXIT_USAGE,
        )
    if not (source / "pyproject.toml").is_file():
        raise CliError(f"{source} enthält keinen LPIC-3-Trainer-Quellcode.", EXIT_USAGE)
    load_env_file()
    say(f"Installierte Version: {_installed_version()}")
    say("Sicherung vor dem Upgrade ...")
    backup_args = argparse.Namespace(to=None, keep=None)
    settings = _settings()
    if settings.db_path.is_file():
        cmd_backup(backup_args)
    was_active = service_active()
    if was_active:
        systemctl("stop", SERVICE_NAME)
    try:
        _copy_source(source, APP_DIR)
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
    if was_active or not args.no_start:
        systemctl("restart", SERVICE_NAME)
    say(f"Upgrade abgeschlossen. Neue Version: {_installed_version()}")
    say(f"Vorherige Programmdateien liegen unter {PREVIOUS_DIR} ('lpic3ctl rollback').")
    return EXIT_OK


def cmd_rollback(args) -> int:
    require_root()
    if not PREVIOUS_DIR.exists():
        raise CliError("Keine vorherige Version vorhanden.", EXIT_MISSING)
    was_active = service_active()
    if was_active:
        systemctl("stop", SERVICE_NAME)
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
    say(
        "Hinweis: Die Datenbank wurde nicht verändert. Bei Schemaänderungen "
        "'lpic3ctl restore' mit der Sicherung vor dem Upgrade nutzen."
    )
    if was_active:
        systemctl("start", SERVICE_NAME)
    return EXIT_OK


def cmd_version(args) -> int:
    say(f"Dieses lpic3ctl:        {__version__}")
    say(f"Installiert:            {_installed_version()}")
    remote = "https://github.com/richtertoralf/LPIC-3-Trainer.git"
    try:
        result = run(
            ["git", "ls-remote", "--tags", "--refs", remote], check=False, capture=True, timeout=15
        )
        tags = sorted(
            (
                line.split("refs/tags/")[-1]
                for line in result.stdout.splitlines()
                if "refs/tags/v" in line
            ),
            key=lambda t: [int(x) if x.isdigit() else 0 for x in t.lstrip("v").split(".")],
        )
        say(f"Neueste Veröffentlichung: {tags[-1] if tags else 'keine Tags gefunden'}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        say("Neueste Veröffentlichung: nicht abrufbar (kein Netz oder git fehlt)")
    return EXIT_OK


def cmd_status(args) -> int:
    load_env_file()
    say(f"Version:       {_installed_version()}")
    if has_systemd() and UNIT_PATH.exists():
        state = systemctl("is-active", SERVICE_NAME, check=False).stdout.strip()
        enabled = systemctl("is-enabled", SERVICE_NAME, check=False).stdout.strip()
        say(f"Dienst:        {state} ({enabled})")
    else:
        say("Dienst:        nicht installiert")
    settings = _settings()
    say(
        f"Datenbank:     {settings.db_path} "
        f"({'vorhanden' if settings.db_path.exists() else 'fehlt'})"
    )
    try:
        from app.db import db_health

        info = db_health()
        say(f"Schema:        {info['schema_version']} (journal {info['journal_mode']})")
    except Exception as exc:
        say(f"Schema:        nicht lesbar ({exc.__class__.__name__})")
    health = _http_health(settings.host, settings.port)
    say(f"Health-Check:  {health}")
    return EXIT_OK


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
        raise CliError("Der Dienst ist nicht installiert.", EXIT_MISSING)
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
        raise CliError("journalctl nicht gefunden.", EXIT_MISSING)
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
    report("Konfiguration", ENV_FILE.is_file(), str(ENV_FILE))
    settings = _settings()
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
        prog="lpic3ctl", description="LPIC-3 Trainer installieren, betreiben und verwalten."
    )
    parser.add_argument("--version", action="version", version=f"lpic3ctl {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("install", help="Anwendung installieren (Root)")
    p.add_argument("--source", help="Quellverzeichnis (Standard: dieses Checkout)")
    p.add_argument("--force", action="store_true", help="bestehende Installation überschreiben")
    p.add_argument("--no-start", action="store_true", help="Dienst nicht starten")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("upgrade", help="Anwendung aktualisieren (Root)")
    p.add_argument("--source", help="Quellverzeichnis mit der neuen Version")
    p.add_argument("--no-start", action="store_true")
    p.set_defaults(func=cmd_upgrade)

    sub.add_parser(
        "rollback", help="vorherige Programmversion wiederherstellen (Root)"
    ).set_defaults(func=cmd_rollback)
    sub.add_parser("version", help="installierte und verfügbare Version anzeigen").set_defaults(
        func=cmd_version
    )
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

    p = sub.add_parser("import", help="Inhaltsdateien (JSON) importieren")
    p.add_argument("files", nargs="+")
    p.add_argument("--visibility", choices=["public", "private"], default=None)
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


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CliError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return exc.code
    except subprocess.CalledProcessError as exc:
        print(f"Fehler: Befehl fehlgeschlagen: {' '.join(exc.cmd)}", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
