"""Template rendering helpers and flash messages."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote, unquote

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from app import __version__
from app.config import PACKAGE_DIR

FLASH_COOKIE = "lpic3_flash"

templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))


def _nl2p(value: str) -> Markup:
    """Render plain text as escaped paragraphs; blank lines separate paragraphs."""
    paragraphs = [p.strip() for p in (value or "").split("\n\n") if p.strip()]
    html = "".join(f"<p>{escape(p).replace(chr(10), Markup('<br>'))}</p>" for p in paragraphs)
    return Markup(html)


def _percent(part: int, total: int) -> int:
    return round(100 * part / total) if total else 0


def _tojson_attr(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


templates.env.filters["nl2p"] = _nl2p
templates.env.filters["percent"] = _percent
templates.env.filters["json_attr"] = _tojson_attr
templates.env.globals["app_version"] = __version__


def _display_choices(question, seed=0):
    from app.services import display_choices

    return display_choices(question, seed)


templates.env.globals["display_choices"] = _display_choices


def render(
    request: Request, name: str, context: dict[str, Any] | None = None, status_code: int = 200
) -> HTMLResponse:
    ctx = {"request": request, "user": getattr(request.state, "user", None)}
    flash_raw = request.cookies.get(FLASH_COOKIE)
    flash = None
    if flash_raw:
        try:
            flash = json.loads(unquote(flash_raw))
        except ValueError:
            flash = None
    ctx["flash"] = flash
    if context:
        ctx.update(context)
    response = templates.TemplateResponse(request, name, ctx, status_code=status_code)
    if flash_raw:
        response.delete_cookie(FLASH_COOKIE)
    return response


def redirect(url: str, flash: str | None = None, kind: str = "info") -> RedirectResponse:
    response = RedirectResponse(url, status_code=303)
    if flash:
        payload = quote(json.dumps({"text": flash, "kind": kind}, ensure_ascii=False))
        response.set_cookie(FLASH_COOKIE, payload, max_age=60, httponly=True, samesite="lax")
    return response
