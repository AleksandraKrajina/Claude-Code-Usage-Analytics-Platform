"""
Ingestion service for loading Claude Code telemetry data.

Reads output from generate_fake_data.py (JSONL batches + employees.csv),
validates events, and stores them in the database.
"""

import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator

from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

# Add project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.database import get_db
from backend.models import TelemetryEvent, Employee

logger = logging.getLogger(__name__)

# Map event body to event_type
EVENT_TYPE_MAP = {
    "claude_code.api_request": "api_request",
    "claude_code.tool_decision": "tool_decision",
    "claude_code.tool_result": "tool_result",
    "claude_code.user_prompt": "user_prompt",
    "claude_code.api_error": "api_error",
}


def _parse_int(value: Any, default: int = 0) -> int:
    """Safely parse integer from string or number."""
    if value is None:
        return default
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def _parse_float(value: Any, default: float = 0.0) -> float:
    """Safely parse float from string or number."""
    if value is None:
        return default
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return default


def _parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse ISO timestamp string to datetime."""
    if not ts_str:
        return None
    try:
        # Format: 2026-01-02T10:30:45.123Z
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def parse_event_message(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a raw telemetry event message into a flat dict for DB insertion.
    
    Args:
        message: Parsed JSON event (body, attributes, resource).
        
    Returns:
        Dict with keys matching TelemetryEvent model, or None if invalid.
    """
    try:
        body = message.get("body", "")
        attrs = message.get("attributes", {})
        resource = message.get("resource", {}) or {}
        
        # Get resource attributes (some are in resource with dots)
        resource_dict = {}
        if isinstance(resource, dict):
            resource_dict = resource
        elif hasattr(resource, "attributes"):
            resource_dict = getattr(resource, "attributes", {})
            
        practice = resource_dict.get("user.practice") or resource_dict.get("user_practice")
        
        event_type = EVENT_TYPE_MAP.get(body, body.replace("claude_code.", ""))
        
        ts_str = attrs.get("event.timestamp", "")
        timestamp = _parse_timestamp(ts_str)
        if not timestamp:
            logger.warning("Skipping event with invalid timestamp: %s", ts_str)
            return None
            
        user_id = attrs.get("user.id") or attrs.get("user_id", "")
        session_id = attrs.get("session.id") or attrs.get("session_id", "")
        
        if not user_id or not session_id:
            logger.warning("Skipping event with missing user_id or session_id")
            return None
        
        record = {
            "user_id": str(user_id)[:64],
            "session_id": str(session_id)[:36],
            "role": str(practice)[:64] if practice else None,
            "project_type": str(practice)[:64] if practice else None,
            "event_type": event_type[:64],
            "timestamp": timestamp,
            "model": attrs.get("model"),
            "input_tokens": _parse_int(attrs.get("input_tokens")),
            "output_tokens": _parse_int(attrs.get("output_tokens")),
            "cache_read_tokens": _parse_int(attrs.get("cache_read_tokens")),
            "cache_creation_tokens": _parse_int(attrs.get("cache_creation_tokens")),
            "cost_usd": _parse_float(attrs.get("cost_usd")),
            "duration_ms": _parse_int(attrs.get("duration_ms")) or None,
            "tool_name": attrs.get("tool_name"),
        }
        
        if record["model"]:
            record["model"] = str(record["model"])[:128]
        if record["tool_name"]:
            record["tool_name"] = str(record["tool_name"])[:64]
            
        return record
        
    except Exception as e:
        logger.exception("Failed to parse event: %s", e)
        return None


def iter_events_from_jsonl(filepath: str) -> Generator[Dict[str, Any], None, None]:
    """
    Iterate over telemetry events from a JSONL file.
    
    Each line is a CloudWatch-style batch with logEvents.
    Each logEvent has a JSON message with the telemetry event.
    
    Args:
        filepath: Path to telemetry_logs.jsonl.
        
    Yields:
        Parsed event dicts ready for DB insertion.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Telemetry logs not found: {filepath}")
    
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                batch = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON at line %d: %s", line_num, e)
                continue
                
            log_events = batch.get("logEvents", [])
            for le in log_events:
                msg_str = le.get("message")
                if not msg_str:
                    continue
                try:
                    msg = json.loads(msg_str)
                except json.JSONDecodeError:
                    continue
                parsed = parse_event_message(msg)
                if parsed:
                    yield parsed


def load_employees_csv(filepath: str) -> List[Dict[str, Any]]:
    """
    Load employees from CSV.
    
    Args:
        filepath: Path to employees.csv.
        
    Returns:
        List of employee dicts with email, full_name, practice, level, location.
    """
    path = Path(filepath)
    if not path.exists():
        logger.warning("Employees file not found: %s", filepath)
        return []
    
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "email": row.get("email", "").strip(),
                "full_name": row.get("full_name", "").strip(),
                "practice": row.get("practice", "").strip() or None,
                "level": row.get("level", "").strip() or None,
                "location": row.get("location", "").strip() or None,
            })
    return rows


def _event_to_row(event: Dict[str, Any]) -> Dict[str, Any]:
    """Convert parsed event dict to DB row (exclude id, created_at)."""
    return {
        "user_id": event["user_id"],
        "session_id": event["session_id"],
        "role": event.get("role"),
        "project_type": event.get("project_type"),
        "event_type": event["event_type"],
        "timestamp": event["timestamp"],
        "model": event.get("model"),
        "input_tokens": event.get("input_tokens", 0),
        "output_tokens": event.get("output_tokens", 0),
        "cache_read_tokens": event.get("cache_read_tokens", 0),
        "cache_creation_tokens": event.get("cache_creation_tokens", 0),
        "cost_usd": event.get("cost_usd", 0.0),
        "duration_ms": event.get("duration_ms"),
        "tool_name": event.get("tool_name"),
    }


def ingest_telemetry(
    jsonl_path: str,
    employees_path: Optional[str] = None,
    batch_size: int = 5000,
    clear_existing: bool = False,
) -> Dict[str, int]:
    """
    Ingest telemetry data from JSONL and optionally employees CSV into the database.
    Uses bulk_insert_mappings for faster inserts.
    """
    stats = {"events_ingested": 0, "employees_ingested": 0, "batches_processed": 0}

    with get_db() as db:
        if clear_existing:
            db.execute(delete(TelemetryEvent))
            db.execute(delete(Employee))
            db.commit()
            logger.info("Cleared existing data.")

        # Ingest events - bulk_insert_mappings is faster than bulk_save_objects
        batch: List[Dict[str, Any]] = []
        for event in iter_events_from_jsonl(jsonl_path):
            batch.append(_event_to_row(event))
            if len(batch) >= batch_size:
                db.execute(TelemetryEvent.__table__.insert(), batch)
                db.commit()
                stats["events_ingested"] += len(batch)
                stats["batches_processed"] += 1
                batch = []

        if batch:
            db.execute(insert(TelemetryEvent.__table__), batch)
            db.commit()
            stats["events_ingested"] += len(batch)
            stats["batches_processed"] += 1

        # Ingest employees (typically small set)
        if employees_path:
            employees = [e for e in load_employees_csv(employees_path) if e.get("email")]
            for emp in employees:
                existing = db.query(Employee).filter(Employee.email == emp["email"]).first()
                if not existing:
                    db.add(Employee(**emp))
            if employees:
                db.commit()
                stats["employees_ingested"] = len(employees)

    logger.info(
        "Ingestion complete: %d events, %d employees",
        stats["events_ingested"],
        stats["employees_ingested"],
    )
    return stats


def run_generate_fake_data(
    num_users: int = 30,
    num_sessions: int = 500,
    days: int = 30,
    output_dir: str = "data",
) -> str:
    """
    Run generate_fake_data.py to produce fresh telemetry data.
    
    Args:
        num_users: Number of fake users.
        num_sessions: Number of sessions.
        days: Days of history.
        output_dir: Output directory for JSONL and CSV.
        
    Returns:
        Path to the output directory.
    """
    project_root = Path(__file__).resolve().parents[2]
    output_path = project_root / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Import and run the generator
    sys.path.insert(0, str(project_root / "claude_code_telemetry"))
    import generate_fake_data as gen
    
    # We need to call main with custom args - the script uses argparse
    # So we'll run it as subprocess or we could refactor to expose a function
    import subprocess
    result = subprocess.run(
        [
            sys.executable,
            str(project_root / "claude_code_telemetry" / "generate_fake_data.py"),
            "--num-users", str(num_users),
            "--num-sessions", str(num_sessions),
            "--days", str(days),
            "--output-dir", str(output_path),
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"generate_fake_data failed: {result.stderr}")
    
    return str(output_path)
