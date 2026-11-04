"""Registration, login, logout and account settings."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import (
    SETTING_REGISTRATION,
    get_current_user,
    get_db,
    get_optional_user,
    get_setting,
    user_count,
)
from app.models import ROLE_ADMIN, ROLE_LEARNER, STATUS_ACTIVE, STATUS_PENDING, User
from app.security import (
    MIN_PASSWORD_LENGTH,
    SESSION_COOKIE,
    create_session,
    delete_session,
    delete_user_sessions,
    hash_password,
    verify_password,
)
from app.web import redirect, render

router = APIRouter()
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")


def _safe_next(url: str | None) -> str:
    if not url or not url.startswith("/") or url.startswith("//"):
        return "/"
    return url


def _set_session_cookie(response, session_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
        path="/",
    )


@router.get("/login")
def login_form(request: Request, next: str = "/", user: User | None = Depends(get_optional_user)):
    if user:
        return redirect("/")
    return render(request, "auth/login.html", {"next": _safe_next(next)})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    user = db.execute(
        select(User).where(User.username == username.strip().lower())
    ).scalar_one_or_none()
    if user is None or not verify_password(user.password_hash, password):
        return render(
            request,
            "auth/login.html",
            {
                "error": "Benutzername oder Passwort ist falsch.",
                "next": _safe_next(next),
                "username": username,
            },
            status_code=400,
        )
    if user.status == STATUS_PENDING:
        return render(
            request,
            "auth/login.html",
            {
                "error": "Das Konto wartet noch auf die Freigabe durch einen Betreuer.",
                "next": _safe_next(next),
                "username": username,
            },
            status_code=403,
        )
    if user.status != STATUS_ACTIVE:
        return render(
            request,
            "auth/login.html",
            {"error": "Das Konto ist deaktiviert.", "next": _safe_next(next), "username": username},
            status_code=403,
        )
    session = create_session(db, user)
    db.commit()
    response = redirect(_safe_next(next))
    _set_session_cookie(response, session.id)
    return response


@router.get("/register")
def register_form(
    request: Request, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)
):
    if user:
        return redirect("/")
    first = user_count(db) == 0
    return render(
        request,
        "auth/register.html",
        {"first_user": first, "mode": get_setting(db, SETTING_REGISTRATION)},
    )


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    display_name: str = Form(""),
    password: str = Form(...),
    password2: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.strip().lower()
    first = user_count(db) == 0
    mode = get_setting(db, SETTING_REGISTRATION)
    ctx = {"first_user": first, "mode": mode, "username": username, "display_name": display_name}
    if not USERNAME_RE.match(username):
        ctx["error"] = (
            "Der Benutzername muss 3 bis 32 Zeichen lang sein und darf nur "
            "Kleinbuchstaben, Ziffern, Punkt, Minus und Unterstrich enthalten."
        )
        return render(request, "auth/register.html", ctx, status_code=400)
    if len(password) < MIN_PASSWORD_LENGTH:
        ctx["error"] = f"Das Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen lang sein."
        return render(request, "auth/register.html", ctx, status_code=400)
    if password != password2:
        ctx["error"] = "Die Passwörter stimmen nicht überein."
        return render(request, "auth/register.html", ctx, status_code=400)
    exists = db.execute(select(User.id).where(User.username == username)).scalar_one_or_none()
    if exists:
        ctx["error"] = "Dieser Benutzername ist bereits vergeben."
        return render(request, "auth/register.html", ctx, status_code=400)
    role = ROLE_ADMIN if first else ROLE_LEARNER
    status = STATUS_ACTIVE if (first or mode == "open") else STATUS_PENDING
    user = User(
        username=username,
        display_name=display_name.strip()[:128],
        password_hash=hash_password(password),
        role=role,
        status=status,
    )
    db.add(user)
    db.flush()
    if status == STATUS_PENDING:
        db.commit()
        return render(request, "auth/pending.html", {})
    session = create_session(db, user)
    db.commit()
    response = redirect(
        "/modules" if not first else "/",
        "Willkommen! Das erste Konto hat Administratorrechte."
        if first
        else "Willkommen! Wähle zuerst deine LPIC-3-Module.",
        "success",
    )
    _set_session_cookie(response, session.id)
    return response


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    delete_session(db, request.cookies.get(SESSION_COOKIE))
    db.commit()
    response = redirect("/login", "Du bist abgemeldet.")
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/account")
def account(request: Request, user: User = Depends(get_current_user)):
    return render(request, "auth/account.html", {})


@router.post("/account/profile")
def account_profile(
    request: Request,
    display_name: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.display_name = display_name.strip()[:128]
    db.add(user)
    return redirect("/account", "Anzeigename gespeichert.", "success")


@router.post("/account/password")
def account_password(
    request: Request,
    current_password: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(user.password_hash, current_password):
        return redirect("/account", "Das aktuelle Passwort ist falsch.", "error")
    if len(password) < MIN_PASSWORD_LENGTH:
        return redirect("/account", f"Mindestens {MIN_PASSWORD_LENGTH} Zeichen.", "error")
    if password != password2:
        return redirect("/account", "Die neuen Passwörter stimmen nicht überein.", "error")
    user.password_hash = hash_password(password)
    db.add(user)
    delete_user_sessions(db, user.id)
    session = create_session(db, user)
    db.commit()
    response = redirect(
        "/account", "Passwort geändert. Andere Sitzungen wurden abgemeldet.", "success"
    )
    _set_session_cookie(response, session.id)
    return response
