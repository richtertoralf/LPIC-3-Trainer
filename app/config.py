"""Application configuration read from environment variables with the LPIC3_ prefix."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PREFIX = "LPIC3_"
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent

DEFAULT_PASSWORD_MIN = 8
DEFAULT_PASSWORD_MAX = 128
PASSWORD_LENGTH_LIMIT = 1024


def _env(name: str, default: str) -> str:
    return os.environ.get(PREFIX + name, default)


class ConfigError(ValueError):
    """An LPIC3_* variable has an invalid value. Reported by the CLI as configuration error."""


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(PREFIX + name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        msg = f"{PREFIX}{name} muss eine ganze Zahl sein, nicht {raw.strip()!r}."
        raise ConfigError(msg) from None


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(PREFIX + name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """Runtime settings. All values can be overridden through LPIC3_* variables."""

    data_dir: Path = field(
        default_factory=lambda: Path(_env("DATA_DIR", str(PROJECT_DIR / "data")))
    )
    content_dir: Path = field(
        default_factory=lambda: Path(_env("CONTENT_DIR", str(PROJECT_DIR / "content")))
    )
    host: str = field(default_factory=lambda: _env("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(_env("PORT", "8000")))
    secure_cookies: bool = field(default_factory=lambda: _env_bool("SECURE_COOKIES", False))
    session_hours: int = field(default_factory=lambda: int(_env("SESSION_HOURS", "720")))
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "info"))
    exam_question_count: int = field(default_factory=lambda: int(_env("EXAM_QUESTIONS", "60")))
    exam_minutes: int = field(default_factory=lambda: int(_env("EXAM_MINUTES", "90")))
    topic_exam_question_count: int = field(
        default_factory=lambda: int(_env("TOPIC_EXAM_QUESTIONS", "15"))
    )
    entry_test_question_count: int = field(
        default_factory=lambda: int(_env("ENTRY_QUESTIONS", "10"))
    )
    # Password policy: only length limits, no complexity rules, no expiry. The defaults
    # keep the behaviour of earlier versions when the variables are not set.
    password_min_length: int = field(
        default_factory=lambda: _env_int("PASSWORD_MIN_LENGTH", DEFAULT_PASSWORD_MIN)
    )
    password_max_length: int = field(
        default_factory=lambda: _env_int("PASSWORD_MAX_LENGTH", DEFAULT_PASSWORD_MAX)
    )

    def __post_init__(self) -> None:
        lo, hi = self.password_min_length, self.password_max_length
        if not 1 <= lo <= PASSWORD_LENGTH_LIMIT:
            raise ConfigError(
                f"LPIC3_PASSWORD_MIN_LENGTH muss zwischen 1 und {PASSWORD_LENGTH_LIMIT} liegen, "
                f"nicht {lo}."
            )
        if not lo <= hi <= PASSWORD_LENGTH_LIMIT:
            raise ConfigError(
                f"LPIC3_PASSWORD_MAX_LENGTH muss zwischen LPIC3_PASSWORD_MIN_LENGTH ({lo}) und "
                f"{PASSWORD_LENGTH_LIMIT} liegen, nicht {hi}."
            )

    @property
    def db_path(self) -> Path:
        explicit = os.environ.get(PREFIX + "DB_PATH")
        if explicit:
            return Path(explicit)
        return self.data_dir / "lpic3-trainer.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached settings object."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Drop the cached settings (used by tests after changing the environment)."""
    global _settings
    _settings = None
