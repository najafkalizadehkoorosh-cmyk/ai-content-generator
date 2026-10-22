"""Local-only SQLite event history."""
from __future__ import annotations
import sqlite3
import threading
from pathlib import Path
from typing import Any


class EventStore:
    def __init__(self, db_path: Path, events_dir: Path):
        self.db_path = Path(db_path)
        self.events_dir = Path(events_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    camera_name TEXT NOT NULL,
                    issue TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    image_path TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)")

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, event: dict[str, Any]) -> int:
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO events(timestamp,camera_name,issue,confidence,image_path) VALUES(?,?,?,?,?)",
                (event["timestamp"], event["camera_name"], event["issue"],
                 float(event["confidence"]), str(event["image_path"]))
            )
            return int(cursor.lastrowid)

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT id,timestamp,camera_name,issue,confidence,image_path FROM events ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 1000)),)
            ).fetchall()
        return [dict(row) for row in rows]

    def count(self) -> int:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()
        return int(row["n"])
