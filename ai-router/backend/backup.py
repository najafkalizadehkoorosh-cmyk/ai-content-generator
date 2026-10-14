"""Create a consistent SQLite backup with Python's standard library."""
from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB = APP_DIR / "backend" / "data" / "ai_router.sqlite3"


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up the local AI Router SQLite database.")
    parser.add_argument("--output", help="Destination .sqlite3 path (defaults to ai-router/backups/)")
    args = parser.parse_args()

    source = Path(os.environ.get("AI_ROUTER_DB", str(DEFAULT_DB))).expanduser().resolve()
    if not source.is_file():
        parser.error(f"Database not found: {source}. Run the local app and save a plan first.")

    if args.output:
        destination = Path(args.output).expanduser().resolve()
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = (APP_DIR / "backups" / f"ai_router_{stamp}.sqlite3").resolve()

    if source == destination:
        parser.error("Backup destination must differ from the live database.")
    if destination.exists():
        parser.error(f"Destination already exists; refusing to overwrite: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(source, timeout=10) as live_db:
            with sqlite3.connect(destination) as backup_db:
                live_db.backup(backup_db)
    except sqlite3.Error as exc:
        if destination.exists():
            destination.unlink()
        parser.error(f"SQLite backup failed: {exc}")

    print(f"Backup created: {destination}")
    print("The live database was not modified.")


if __name__ == "__main__":
    main()
