"""Password hashing (Argon2id) and server-side session handling."""

from __future__ import annotations

import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import STATUS_ACTIVE, User, UserSession, utcnow

_hasher = PasswordHasher()  # argon2id is the library default

SESSION_COOKIE = "lpic3_session"
_PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def password_policy() -> tuple[int, int]:
    """Return (min_length, max_length) from the configuration."""
    settings = get_settings()
    return settings.password_min_length, settings.password_max_length


def password_error(password: str) -> str | None:
    """Return a German error message when the password violates the length policy.

    Used by every place that sets a password (registration, password change, user creation
    in the web interface and on the CLI). Existing hashes are never re-validated, so a
    stricter policy does not lock out existing accounts.
    """
    lo, hi = password_policy()
    if len(password) < lo:
        return f"Das Passwort muss mindestens {lo} Zeichen lang sein."
    if len(password) > hi:
        return f"Das Passwort darf höchstens {hi} Zeichen lang sein."
    return None


def generate_password() -> str:
    """Random start password (admin reset) that satisfies the configured policy."""
    lo, hi = password_policy()
    length = min(max(12, lo), hi)
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_session(db: Session, user: User) -> UserSession:
    """Create a new database session row and return it."""
    settings = get_settings()
    session = UserSession(
        id=secrets.token_urlsafe(32),
        user_id=user.id,
        expires_at=utcnow() + timedelta(hours=settings.session_hours),
    )
    db.add(session)
    db.flush()
    return session


def resolve_session(db: Session, session_id: str | None) -> User | None:
    """Return the active user for a session id, or None."""
    if not session_id:
        return None
    row = db.execute(select(UserSession).where(UserSession.id == session_id)).scalar_one_or_none()
    if row is None:
        return None
    if row.expires_at < utcnow():
        db.delete(row)
        db.flush()
        return None
    user = db.get(User, row.user_id)
    if user is None or user.status != STATUS_ACTIVE:
        return None
    return user


def delete_session(db: Session, session_id: str | None) -> None:
    if session_id:
        db.execute(delete(UserSession).where(UserSession.id == session_id))


def delete_user_sessions(db: Session, user_id: int) -> None:
    db.execute(delete(UserSession).where(UserSession.user_id == user_id))


def purge_expired_sessions(db: Session) -> int:
    result = db.execute(delete(UserSession).where(UserSession.expires_at < utcnow()))
    return result.rowcount or 0
