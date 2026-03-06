"""
Ingestion API endpoints.

Provides endpoints to load telemetry data, trigger ingestion,
and real-time event streaming (bonus feature).
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
from backend.database import SessionLocal
from backend.models import TelemetryEvent
from backend.services.ingestion import (
    ingest_telemetry,
    parse_event_message,
    run_generate_fake_data,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class IngestResponse(BaseModel):
    """Response model for ingest endpoint."""

    events_ingested: int
    employees_ingested: int
    batches_processed: int


def _find_telemetry_files(project_root: Path) -> tuple[Optional[str], Optional[str]]:
    """Find telemetry_logs.jsonl and employees.csv in data/ or output/."""
    for subdir in ("data", "output"):
        jpath = project_root / subdir / "telemetry_logs.jsonl"
        epath = project_root / subdir / "employees.csv"
        if jpath.exists():
            return str(jpath), str(epath) if epath.exists() else None
    return None, None


def _get_project_root() -> Path:
    """Resolve project root from this file's location (backend/routers/ingestion.py -> project root)."""
    root = Path(__file__).resolve().parents[2]
    # Fallback: if data/ not found, try cwd (e.g. when run from project root)
    if not (root / "data" / "telemetry_logs.jsonl").exists() and not (root / "output" / "telemetry_logs.jsonl").exists():
        cwd = Path.cwd()
        if (cwd / "data" / "telemetry_logs.jsonl").exists() or (cwd / "output" / "telemetry_logs.jsonl").exists():
            return cwd
    return root


@router.get("/load/status")
def load_status():
    """Return paths and existence for debugging. Helps verify data file is found."""
    root = _get_project_root()
    jpath, epath = _find_telemetry_files(root)
    jpath = jpath or str(root / "data" / "telemetry_logs.jsonl")
    return {
        "project_root": str(root),
        "telemetry_path": jpath,
        "telemetry_exists": Path(jpath).exists(),
        "employees_path": epath,
        "employees_exists": Path(epath).exists() if epath else False,
    }


@router.post("/load", response_model=IngestResponse)
def load_data(
    jsonl_path: Optional[str] = Query(default=None),
    employees_path: Optional[str] = Query(default=None),
    clear_existing: bool = Query(default=True),
):
    """
    Ingest telemetry data from JSONL file and optionally employees CSV.
    
    If paths not provided, auto-detects in data/ or output/ (from generate_fake_data.py).
    """
    project_root = _get_project_root()
    
    if jsonl_path:
        jpath = jsonl_path
        epath = employees_path or str(Path(jsonl_path).parent / "employees.csv")
    else:
        jpath, epath = _find_telemetry_files(project_root)
        jpath = jpath or settings.telemetry_logs_path or str(project_root / "data" / "telemetry_logs.jsonl")
        epath = epath or settings.employees_csv_path or str(project_root / "data" / "employees.csv")
    
    if not Path(jpath).exists():
        raise HTTPException(
            status_code=404,
            detail=f"Telemetry file not found. Run generate_fake_data.py or click 'Generate & Load' first.",
        )
    
    epath_use = epath if epath and Path(epath).exists() else None
    try:
        stats = ingest_telemetry(
            jsonl_path=jpath,
            employees_path=epath_use,
            clear_existing=clear_existing,
        )
        return IngestResponse(**stats)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Ingestion failed: %s", e)
        err_msg = str(e)
        if "no such table" in err_msg.lower() or "operational" in err_msg.lower():
            err_msg = f"Database error: {err_msg}. Ensure the backend has started (tables are created on startup)."
        raise HTTPException(status_code=500, detail=err_msg)


class GenerateResponse(BaseModel):
    """Response for generate endpoint."""

    output_dir: str
    message: str


class StreamEventItem(BaseModel):
    """Single event for streaming ingestion."""

    body: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    resource: Dict[str, Any] = Field(default_factory=dict)
    scope: Optional[Dict[str, Any]] = None


class StreamEventsRequest(BaseModel):
    """Request body for real-time event streaming."""

    events: List[StreamEventItem]


@router.post("/stream")
def stream_events(payload: StreamEventsRequest):
    """
    Real-time streaming: ingest a batch of events immediately.

    Demonstrates how the system could handle live data streaming.
    Events are validated and persisted in real time.
    """
    ingested = 0
    db = SessionLocal()
    try:
        for ev in payload.events:
            msg = {
                "body": ev.body,
                "attributes": ev.attributes,
                "resource": ev.resource,
            }
            parsed = parse_event_message(msg)
            if parsed:
                db.add(TelemetryEvent(**parsed))
                ingested += 1
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
    return {"ingested": ingested, "total_received": len(payload.events)}


@router.post("/generate-and-load", response_model=IngestResponse)
def generate_and_load(
    num_users: int = Query(default=30, ge=1, le=500),
    num_sessions: int = Query(default=500, ge=1, le=10000),
    days: int = Query(default=30, ge=1, le=365),
):
    """
    Generate fake telemetry and ingest in one call. Use for quick setup.
    """
    try:
        output_dir = run_generate_fake_data(
            num_users=num_users,
            num_sessions=num_sessions,
            days=days,
            output_dir="data",
        )
        jpath = str(Path(output_dir) / "telemetry_logs.jsonl")
        epath = str(Path(output_dir) / "employees.csv")
        stats = ingest_telemetry(
            jsonl_path=jpath,
            employees_path=epath if Path(epath).exists() else None,
            clear_existing=True,
        )
        return IngestResponse(**stats)
    except Exception as e:
        logger.exception("Generate and load failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=GenerateResponse)
def generate_fake_data(
    num_users: int = Query(default=30, ge=1, le=500),
    num_sessions: int = Query(default=500, ge=1, le=10000),
    days: int = Query(default=30, ge=1, le=365),
):
    """
    Run generate_fake_data.py to create fresh synthetic telemetry.
    Output is written to data/ directory.
    """
    try:
        output_dir = run_generate_fake_data(
            num_users=num_users,
            num_sessions=num_sessions,
            days=days,
            output_dir="data",
        )
        return GenerateResponse(
            output_dir=output_dir,
            message=f"Generated data in {output_dir}. Call POST /ingest/load to load into database.",
        )
    except Exception as e:
        logger.exception("Generate failed")
        raise HTTPException(status_code=500, detail=str(e))
