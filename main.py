#!/usr/bin/env python3
"""
Network Bug Triage & Remediation Platform - FastAPI Backend

High-performance ASGI backend providing:
  - Full telemetry ingestion, synthetic fault injection, and triage pipeline
  - Rule-based, NLP-based, and XGBoost machine-learning triage execution
  - Multi-agent AI reasoning (Gemini/Vertex AI or graceful heuristic degradation)
  - Remediation proposal, human-approval workflow, and audit logging
  - CORS support for future React UI (http://localhost:5173)
  - Auto-generated OpenAPI / Swagger documentation (/docs and /redoc)
  - Backward-compatible serving of existing templates/dashboard.html at /

Usage:
    uvicorn main:app --reload --port 8000
    or:
    python main.py
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from api.routes import public_router, router as api_router
from api.voice_routes import voice_public_router, voice_router

# ---------------------------------------------------------------------------
# App Initialization & Metadata
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Network Bug Triage & Remediation Platform API",
    description=(
        "Automated detection, correlation, and remediation platform for "
        "network and RDMA kernel issues across distributed infrastructure."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------------
# Configured for upcoming React frontend (Vite defaults to localhost:5173)
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Allow custom origins from environment variable if provided
env_origins = os.environ.get("NBT_CORS_ORIGINS")
if env_origins:
    allowed_origins.extend([origin.strip() for origin in env_origins.split(",") if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Mount Routers
# ---------------------------------------------------------------------------
app.include_router(public_router, prefix="/api")
app.include_router(api_router, prefix="/api")
app.include_router(voice_public_router, prefix="/api")
app.include_router(voice_router, prefix="/api")

# ---------------------------------------------------------------------------
# Root / Dashboard Endpoint
# ---------------------------------------------------------------------------
DASHBOARD_HTML_PATH = ROOT / "templates" / "dashboard.html"
FRONTEND_INDEX_PATH = ROOT / "static" / "index.html"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index():
    """
    Serve the compiled React application when present, with the legacy dashboard
    as a development/source-checkout fallback.
    """
    if FRONTEND_INDEX_PATH.exists():
        return FileResponse(FRONTEND_INDEX_PATH, media_type="text/html")
    if DASHBOARD_HTML_PATH.exists():
        return FileResponse(DASHBOARD_HTML_PATH, media_type="text/html")
    return HTMLResponse("<h2>Network Bug Triage Platform API is running. Visit <a href='/docs'>/docs</a>.</h2>")


@app.get("/assets/{asset_path:path}", include_in_schema=False)
async def frontend_asset(asset_path: str):
    """Serve Vite's hashed assets from the same Cloud Run service as the API."""
    asset_root = ROOT / "static" / "assets"
    candidate = (asset_root / asset_path).resolve()
    if asset_root.resolve() not in candidate.parents or not candidate.is_file():
        return HTMLResponse("Not Found", status_code=404)
    return FileResponse(candidate)


@app.get("/{asset_name}", include_in_schema=False)
async def frontend_root_asset(asset_name: str):
    """Serve root-level public files copied by Vite (for example the favicon)."""
    candidate = (ROOT / "static" / asset_name).resolve()
    static_root = (ROOT / "static").resolve()
    if static_root not in candidate.parents or not candidate.is_file():
        return HTMLResponse("Not Found", status_code=404)
    return FileResponse(candidate)


# ---------------------------------------------------------------------------
# Server Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(ROOT / "logs", exist_ok=True)
    os.makedirs(ROOT / "controller" / "models", exist_ok=True)

    host = os.environ.get("NBT_FASTAPI_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("NBT_FASTAPI_PORT", "8000"))
    except ValueError:
        port = 8000

    print("=" * 64)
    print("  Network Bug Triage & Remediation Platform — FastAPI")
    print(f"  Interactive Docs (Swagger) : http://{host}:{port}/docs")
    print(f"  Alternative Docs (ReDoc)   : http://{host}:{port}/redoc")
    print(f"  Live Web Dashboard         : http://{host}:{port}/")
    print("=" * 64)
    if host not in ("127.0.0.1", "localhost", "::1") and not os.environ.get("NBT_API_KEY"):
        print("  WARNING: bound to a non-loopback address with NBT_API_KEY unset;")
        print("  the API (including remediation approval) is unauthenticated.")
        print("=" * 64)

    # Cloud Run injects PORT and requires the container to bind on 0.0.0.0.
    cloud_run = bool(os.environ.get("K_SERVICE"))
    host = "0.0.0.0" if cloud_run else host
    port = int(os.environ.get("PORT", port))
    uvicorn.run("main:app", host=host, port=port, reload=not cloud_run)
