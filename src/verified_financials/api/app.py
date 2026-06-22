"""FastAPI application factory.

The DTOs double as response models, so the auto-generated OpenAPI schema at
``/docs`` is ready for the deferred frontend to consume directly.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .._env import load_env
from ..loaders.base import DataError
from .routes import router

logger = logging.getLogger("verified_financials")

# Load <repo-root>/.env (if present) before reading any configuration from the
# environment, so OPENAI_API_KEY / VFIN_* "just work" under uvicorn.
load_env()

# Comma-separated allowed origins; defaults to the Vite dev server.
_CORS_ORIGINS = os.environ.get(
    "VFIN_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

# Built SPA (frontend/dist) — served at one URL when present.
_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sentinel API",
        version="0.1.0",
        description=(
            "Verification / tie-out, borrowing base certificate, and FCCR covenant "
            "engines over a provenance-tracked fact store."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in _CORS_ORIGINS if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.exception_handler(DataError)
    async def _data_error(_request: Request, exc: DataError):
        # Bad/garbled cell value in a source file → friendly, actionable message.
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception):
        # Never leak a stack trace to the client; log it server-side instead.
        logger.exception("Unhandled error serving request", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong while computing — check the inputs and try again."},
        )

    # Serve the built SPA last so API routes always take precedence; any other
    # path returns index.html for client-side routing.
    if (_DIST / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):  # noqa: ARG001 - path captured for routing only
            return FileResponse(_DIST / "index.html")

    return app


app = create_app()
