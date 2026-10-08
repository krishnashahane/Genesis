"""FastAPI application factory with Runtime lifecycle management."""

from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from genesis import __version__
from genesis.api.routes import router
from genesis.config import get_settings
from genesis.core.runtime import Runtime

_WEB_DIR = Path(__file__).resolve().parents[2] / "web"


def create_app(runtime: Runtime | None = None) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        rt = runtime or Runtime(settings)
        await rt.start()
        app.state.runtime = rt
        try:
            yield
        finally:
            await rt.stop()

    app = FastAPI(
        title="Genesis OS",
        version=__version__,
        description="Runtime and memory operating system for autonomous AI agents.",
        lifespan=lifespan,
    )
    origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]

    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "Authorization", "X-Genesis-API-Key"],
        )

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.max_request_bytes:
                    from fastapi.responses import JSONResponse
                    return JSONResponse({"detail": "request body too large"}, status_code=413)
            except ValueError:
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "invalid content-length"}, status_code=400)

        if (
            settings.env == "production"
            and request.url.path.startswith("/api/")
            and request.url.path != "/api/health"
        ):
            supplied = request.headers.get("X-Genesis-API-Key", "")
            if not settings.api_key or not secrets.compare_digest(supplied, settings.api_key):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "authentication required"}, status_code=401)

        return await call_next(request)

    app.include_router(router, prefix="/api")

    if _WEB_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_WEB_DIR)), name="static")

        @app.get("/", include_in_schema=False)
        async def index() -> FileResponse:
            return FileResponse(str(_WEB_DIR / "index.html"))

    return app


# Convenience for `uvicorn genesis.api.app:app`
if os.getenv("GENESIS_AUTOAPP") != "0":
    app = create_app()
