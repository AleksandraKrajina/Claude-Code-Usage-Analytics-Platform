#!/usr/bin/env python3
"""
Generate fake telemetry data and ingest into the database.

Run from project root:
    python scripts/generate_and_ingest.py [--num-users 30] [--num-sessions 500] [--days 30]
"""

import argparse
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from backend.database import init_db
from backend.services.ingestion import ingest_telemetry, run_generate_fake_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-users", type=int, default=30)
    parser.add_argument("--num-sessions", type=int, default=500)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--no-ingest", action="store_true", help="Only generate, do not ingest")
    args = parser.parse_args()

    print("Initializing database...")
    init_db()

    print("Generating fake telemetry data...")
    output_dir = run_generate_fake_data(
        num_users=args.num_users,
        num_sessions=args.num_sessions,
        days=args.days,
        output_dir="data",
    )
    print(f"  Output: {output_dir}")

    if args.no_ingest:
        print("Skipping ingestion (--no-ingest)")
        return

    print("Ingesting into database...")
    stats = ingest_telemetry(
        jsonl_path=str(Path(output_dir) / "telemetry_logs.jsonl"),
        employees_path=str(Path(output_dir) / "employees.csv"),
        clear_existing=True,
    )
    print(f"  Ingested: {stats['events_ingested']} events, {stats['employees_ingested']} employees")


if __name__ == "__main__":
    main()
