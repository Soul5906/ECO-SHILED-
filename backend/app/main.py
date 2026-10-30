"""ECO-SHIELD FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config.settings import get_settings
from app.storage.database import init_db

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("ecoshield")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise database."""
    logger.info("ECO-SHIELD starting — initialising database…")
    init_db()
    logger.info("Database ready.")
    yield
    logger.info("ECO-SHIELD shutting down.")


app = FastAPI(
    title="ECO-SHIELD API",
    description=(
        "Evidence-Driven Clean Energy & Environmental Diagnostics. "
        "Analyses solar-energy telemetry, detects anomalies, diagnoses possible root causes, "
        "and recommends next diagnostic steps."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler — never expose stack traces to client
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected server error occurred.", "detail": None},
    )


# Mount all routes under /api prefix
app.include_router(router, prefix="/api")

# Static frontend serving in production
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIST = os.environ.get(
    "FRONTEND_DIST_DIR",
    str(Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"),
)

if os.path.isdir(FRONTEND_DIST) and os.path.isfile(os.path.join(FRONTEND_DIST, "index.html")):
    assets_path = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api") or full_path in ("docs", "redoc", "openapi.json"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        target_file = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(target_file):
            return FileResponse(target_file)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
else:
    @app.get("/", tags=["System"])
    async def root():
        return {"name": "ECO-SHIELD API", "version": settings.app_version, "docs": "/docs"}

