"""FastAPI application factory with lifecycle, auth and request hardening."""

from __future__ import annotations

import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from genesis import __version__
from genesis.api.routes import router
from genesis.config import get_settings
from genesis.core.runtime import Runtime

_WEB_DIR = Path(__file__).resolve().parents[2] / "web"


def create_app(runtime: Runtime | None = None) -> FastAPI:
    settings = runtime.settings if runtime is not None else get_settings()

    if settings.env == "production" and not settings.api_key:
        raise RuntimeError("GENESIS_API_KEY must be set when GENESIS_ENV=production.")

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

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "X-Genesis-API-Key"],
            allow_credentials=False,
        )

    rate_state: dict[str, tuple[float, int]] = {}

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        now = time.monotonic()
        path = request.url.path

        app_key = request.client.host if request.client else "unknown"

        if path.startswith("/api/") and request.method not in {"OPTIONS"}:
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > settings.max_request_bytes:
                        return JSONResponse(
                            {"detail": "request body too large"},
                            status_code=413,
                        )
                except ValueError:
                    return JSONResponse(
                        {"detail": "invalid content-length"},
                        status_code=400,
                    )

            if path != "/api/health":
                supplied = request.headers.get("X-Genesis-API-Key", "")
                if settings.env == "production" and not secrets.compare_digest(
                    supplied, settings.api_key
                ):
                    return JSONResponse(
                        {"detail": "authentication required"},
                        status_code=401,
                    )

                window_start, count = rate_state.get(app_key, (now, 0))
                if now - window_start >= 60:
                    window_start, count = now, 0
                if count >= settings.rate_limit_per_minute:
                    retry_after = max(1, int(60 - (now - window_start)))
                    response = JSONResponse(
                        {"detail": "rate limit exceeded"},
                        status_code=429,
                    )
                    response.headers["Retry-After"] = str(retry_after)
                    return response
                rate_state[app_key] = (window_start, count + 1)

                if len(rate_state) > 5000:
                    stale_before = now - 60
                    rate_state.clear()
                    rate_state[app_key] = (stale_before, 1)

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    app.include_router(router, prefix="/api")

    if _WEB_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_WEB_DIR)), name="static")

        @app.get("/", include_in_schema=False)
        async def index() -> FileResponse:
            return FileResponse(str(_WEB_DIR / "index.html"))

    return app


if os.getenv("GENESIS_AUTOAPP") != "0":
    app = create_app()
