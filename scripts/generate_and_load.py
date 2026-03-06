#!/usr/bin/env python3
"""
Generate fake telemetry data and load into PostgreSQL.

Production-ready script for local development. Connects to Docker PostgreSQL,
runs generate_fake_data.py, and ingests into telemetry_events.

Usage:
    # From project root (ensure PostgreSQL is running: docker-compose up -d postgres)
    python scripts/generate_and_load.py

    # Custom parameters
    python scripts/generate_and_load.py --num-users 100 --num-sessions 5000 --days 60

    # With custom DB (e.g. different host)
    DATABASE_URL=postgresql://user:pass@host:5432/db python scripts/generate_and_load.py
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Set PostgreSQL before any backend imports
_DEFAULT_DB_URL = "postgresql://postgres:postgres@localhost:5432/claude_analytics"
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = _DEFAULT_DB_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def wait_for_postgres(url: str, max_attempts: int = 30, delay_sec: float = 1.0) -> bool:
    """
    Wait for PostgreSQL to be ready (handles Docker startup delay).
    
    Returns:
        True if connection succeeds, False otherwise.
    """
    try:
        import psycopg2
        from urllib.parse import urlparse, unquote
    except ImportError:
        logger.warning("psycopg2 not installed; skipping pre-connection check")
        return True

    parsed = urlparse(url)
    config = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": unquote(parsed.username) if parsed.username else "postgres",
        "password": unquote(parsed.password) if parsed.password else "",
        "dbname": (parsed.path or "").lstrip("/") or "postgres",
    }

    for attempt in range(1, max_attempts + 1):
        try:
            conn = psycopg2.connect(**config)
            conn.close()
            logger.info("PostgreSQL is ready")
            return True
        except Exception as e:
            logger.warning("Attempt %d/%d: %s", attempt, max_attempts, e)
            if attempt < max_attempts:
                time.sleep(delay_sec)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate telemetry and load into PostgreSQL")
    parser.add_argument("--num-users", type=int, default=100, help="Number of fake users")
    parser.add_argument("--num-sessions", type=int, default=5000, help="Number of sessions")
    parser.add_argument("--days", type=int, default=60, help="Days of history")
    parser.add_argument("--output-dir", type=str, default="data", help="Output directory for JSONL")
    parser.add_argument("--append", action="store_true",
                        help="Append to existing data (default: truncate before load)")
    parser.add_argument("--skip-wait", action="store_true", help="Skip PostgreSQL readiness check")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)
    sys.path.insert(0, str(project_root))

    db_url = os.environ.get("DATABASE_URL", _DEFAULT_DB_URL)
    safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
    logger.info("Database: ***@%s", safe_url)

    if not args.skip_wait and "postgresql" in db_url:
        if not wait_for_postgres(db_url):
            logger.error("PostgreSQL not ready after retries. Is Docker running? docker-compose up -d postgres")
            return 1

    try:
        from backend.database import init_db
        from backend.services.ingestion import ingest_telemetry, run_generate_fake_data
    except ImportError as e:
        logger.error("Import failed. Run from project root: python scripts/generate_and_load.py")
        logger.error("Error: %s", e)
        return 1

    # 1. Ensure tables exist
    logger.info("Creating tables if not exist...")
    init_db()

    # 2. Generate fake data
    logger.info("Generating %d users, %d sessions, %d days...", args.num_users, args.num_sessions, args.days)
    try:
        output_dir = run_generate_fake_data(
            num_users=args.num_users,
            num_sessions=args.num_sessions,
            days=args.days,
            output_dir=args.output_dir,
        )
    except RuntimeError as e:
        logger.error("Generation failed: %s", e)
        return 1

    jsonl_path = Path(output_dir) / "telemetry_logs.jsonl"
    employees_path = Path(output_dir) / "employees.csv"

    if not jsonl_path.exists():
        logger.error("Generated file not found: %s", jsonl_path)
        return 1

    # 3. Ingest into PostgreSQL
    clear = not args.append
    if clear:
        logger.info("Clearing existing data and ingesting...")
    else:
        logger.info("Appending to existing data...")
    try:
        stats = ingest_telemetry(
            jsonl_path=str(jsonl_path),
            employees_path=str(employees_path) if employees_path.exists() else None,
            batch_size=1000,
            clear_existing=clear,
        )
    except Exception as e:
        logger.exception("Ingestion failed: %s", e)
        return 1

    logger.info("Done. Events: %d, Employees: %d, Batches: %d",
                stats["events_ingested"], stats["employees_ingested"], stats["batches_processed"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
