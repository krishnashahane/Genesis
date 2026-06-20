"""FastAPI application factory with Runtime lifecycle management."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
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
