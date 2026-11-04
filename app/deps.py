"""FastAPI dependencies: database session, current user and role checks."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session_factory
from app.models import ROLE_ADMIN, AppSetting, User
from app.security import SESSION_COOKIE, resolve_session


def get_db() -> Iterator[Session]:
    db = get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user = resolve_session(db, request.cookies.get(SESSION_COOKIE))
    request.state.user = user
    return user


class LoginRequired(Exception):
    """Raised when an anonymous visitor requests a protected page."""

    def __init__(self, next_url: str):
        self.next_url = next_url


def get_current_user(request: Request, user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        if request.headers.get("accept", "").startswith(
            "application/json"
        ) or request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Anmeldung erforderlich"
            )
        raise LoginRequired(str(request.url.path))
    return user


def require_supervisor(user: User = Depends(get_current_user)) -> User:
    if not user.is_supervisor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")
    return user


# ------------------------------------------------------------------ app settings

SETTING_REGISTRATION = "registration_mode"  # open | approval
SETTING_DEFAULTS = {SETTING_REGISTRATION: "open"}


def get_setting(db: Session, key: str) -> str:
    row = db.get(AppSetting, key)
    return row.value if row else SETTING_DEFAULTS.get(key, "")


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value
    db.flush()


def user_count(db: Session) -> int:
    return db.execute(select(func.count(User.id))).scalar_one()
