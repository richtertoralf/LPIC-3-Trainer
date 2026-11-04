"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from urllib.parse import quote, urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app import __version__
from app.config import PACKAGE_DIR, get_settings
from app.db import db_health, reset_engine, session_scope
from app.deps import LoginRequired
from app.migrate import upgrade_database
from app.routers import admin, api, auth, exam, labs, learn, pages, vocab
from app.security import purge_expired_sessions
from app.web import render

log = logging.getLogger("lpic3")


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Reject state-changing requests whose Origin does not match the Host header."""

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin")
            if origin and origin != "null":
                origin_host = urlsplit(origin).netloc
                host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
                if origin_host and origin_host != host:
                    return JSONResponse({"detail": "Ungültiger Origin"}, status_code=403)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    upgrade_database()
    with session_scope() as db:
        removed = purge_expired_sessions(db)
    if removed:
        log.info("removed %s expired sessions", removed)
    log.info("LPIC-3 Trainer %s ready (database %s)", __version__, settings.db_path)
    yield
    reset_engine()


def create_app() -> FastAPI:
    app = FastAPI(title="LPIC-3 Trainer", version=__version__, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(OriginCheckMiddleware)
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")

    for router in (auth.router, pages.router, learn.router, exam.router, vocab.router,
                   labs.router, admin.router, api.router):
        app.include_router(router)

    @app.get("/health", include_in_schema=False)
    def health():
        try:
            info = db_health()
        except Exception as exc:  # pragma: no cover - only on broken installations
            return JSONResponse({"status": "error", "detail": str(exc)}, status_code=503)
        return {"status": "ok", "version": __version__, "database": info}

    @app.exception_handler(LoginRequired)
    async def login_required_handler(request: Request, exc: LoginRequired):
        return RedirectResponse(f"/login?next={quote(exc.next_url)}", status_code=303)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if request.url.path.startswith("/api/") or request.headers.get("accept", "").startswith(
            "application/json"
        ):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        if not hasattr(request.state, "user"):
            request.state.user = None
        return render(request, "error.html", {"status_code": exc.status_code, "detail": exc.detail},
                      status_code=exc.status_code)

    return app


app = create_app()

__all__ = ["app", "create_app", "HTTPException"]
