"""
Claude Code Usage Analytics API.

FastAPI application providing REST endpoints for telemetry ingestion,
analytics metrics, and anomaly detection.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend.config import settings
from backend.database import init_db
from backend.routers import analytics, ingestion

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: init db on startup."""
    init_db()
    yield
    # Shutdown: nothing to do


app = FastAPI(
    title="Claude Code Usage Analytics API",
    description="REST API for Claude Code telemetry analytics, metrics, and anomaly detection.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics.router, prefix=settings.api_prefix)
app.include_router(ingestion.router, prefix=settings.api_prefix)


@app.get("/")
def root():
    """Redirect to API docs."""
    return RedirectResponse(url="/docs", status_code=302)


@app.get("/api/v1/health")
def health():
    """Health check and API info."""
    return {
        "service": "Claude Code Usage Analytics API",
        "version": "1.0.0",
        "docs": "/docs",
        "dashboard": "Run: python -m streamlit run dashboard/app.py (port 8501)",
    }
