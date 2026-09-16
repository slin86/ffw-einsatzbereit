import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from einsatzbereit.config import get_settings
from einsatzbereit.db import get_sessionmaker
from einsatzbereit.routers import audit, auth, catalog, me, members, overview, users
from einsatzbereit.seed import run_initial_seed

logging.basicConfig(level=logging.INFO)

CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
    "base-uri 'self'; form-action 'self'"
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """
    Checks the configuration for unsafe production settings and runs the one time initial seed
    before the application accepts requests.
    """
    get_settings().check_production_safety()
    with get_sessionmaker()() as db:
        run_initial_seed(db)
    yield


def create_app() -> FastAPI:
    """
    Builds the application with security headers, all API routers, health endpoints and, if a
    built frontend exists, the single page application.
    """
    app = FastAPI(title="Einsatzbereit", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    for r in (
        auth.router,
        me.router,
        users.router,
        catalog.router,
        members.router,
        overview.router,
        audit.router,
    ):
        app.include_router(r)

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    def readyz() -> dict[str, str]:
        with get_sessionmaker()() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok"}

    _mount_spa(app, Path(get_settings().static_dir))
    return app


def _mount_spa(app: FastAPI, static_dir: Path) -> None:
    """
    Serves the built frontend. Asset files are served directly, every other path outside the API
    returns the index page so that client side routes work. Paths that resolve outside the static
    directory also get the index page, which prevents path traversal.
    """
    index = static_dir / "index.html"
    if not index.is_file():
        return
    if (static_dir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
    root = static_dir.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(404)
        candidate = (static_dir / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


app = create_app()
