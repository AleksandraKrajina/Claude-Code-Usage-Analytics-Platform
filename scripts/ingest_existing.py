#!/usr/bin/env python3
"""
Ingest existing telemetry data from data/ directory.

Use when you have already run generate_fake_data.py and want to load
the output into the database without regenerating.

Run from project root:
    python scripts/ingest_existing.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from backend.database import init_db
from backend.services.ingestion import ingest_telemetry


def main():
    init_db()
    jsonl = project_root / "data" / "telemetry_logs.jsonl"
    employees = project_root / "data" / "employees.csv"
    if not jsonl.exists():
        print(f"Error: {jsonl} not found. Run generate_fake_data.py first.")
        sys.exit(1)
    stats = ingest_telemetry(
        jsonl_path=str(jsonl),
        employees_path=str(employees) if employees.exists() else None,
        clear_existing=True,
    )
    print(f"Ingested: {stats['events_ingested']} events, {stats['employees_ingested']} employees")


if __name__ == "__main__":
    main()
