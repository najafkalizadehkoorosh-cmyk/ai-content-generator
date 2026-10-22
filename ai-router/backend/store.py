"""SQLite persistence for the local-first AI Router MVP. Standard library only."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StoreError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class Store:
    """Small SQLite repository; each operation owns its own connection."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as db, db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS plans (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL,
                    fingerprint TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('draft', 'approved', 'simulated', 'cancelled', 'failed')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(project_id, version)
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
                    task_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('planned', 'simulated', 'cancelled', 'failed')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(plan_id, task_key)
                );
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
                    attempt INTEGER NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('running', 'succeeded', 'failed')),
                    prompt_chars INTEGER NOT NULL DEFAULT 0,
                    output_text TEXT NOT NULL DEFAULT '',
                    error_message TEXT NOT NULL DEFAULT '',
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(plan_id, attempt)
                );
                CREATE INDEX IF NOT EXISTS idx_agent_runs_plan_attempt
                    ON agent_runs(plan_id, attempt DESC);
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    plan_id TEXT REFERENCES plans(id) ON DELETE SET NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_plans_project_updated
                    ON plans(project_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_events_project_created
                    ON audit_events(project_id, created_at DESC);
                """
            )

    @staticmethod
    def _project(row: sqlite3.Row) -> dict[str, Any]:
        return {key: row[key] for key in ("id", "name", "description", "created_at", "updated_at")}

    @staticmethod
    def _plan(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "version": row["version"],
            "fingerprint": row["fingerprint"],
            "plan": json.loads(row["payload_json"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_workspace(self) -> dict[str, Any]:
        now = utc_now()
        with closing(self._connect()) as db, db:
            db.execute(
                """
                INSERT OR IGNORE INTO projects (id, name, description, created_at, updated_at)
                VALUES ('default', 'AI Router Workspace', 'پروژه محلی پیش‌فرض', ?, ?)
                """,
                (now, now),
            )
            row = db.execute("SELECT * FROM projects WHERE id = 'default'").fetchone()
            project = self._project(row)
        return {"project": project, "recent_plans": self.list_plans("default", 12)}

    def list_plans(self, project_id: str = "default", limit: int = 12) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 50))
        with closing(self._connect()) as db, db:
            rows = db.execute(
                """
                SELECT id, project_id, version, payload_json, status, created_at, updated_at,
                    (SELECT ar.status FROM agent_runs ar
                     WHERE ar.plan_id = plans.id ORDER BY ar.attempt DESC LIMIT 1) AS agent_status
                FROM plans WHERE project_id = ?
                ORDER BY version DESC LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "version": row["version"],
                "title": json.loads(row["payload_json"]).get("title", "بدون عنوان"),
                "status": row["status"],
                "agent_status": row["agent_status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    @staticmethod
    def _agent_run(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "plan_id": row["plan_id"], "attempt": row["attempt"],
            "model": row["model"], "status": row["status"], "prompt_chars": row["prompt_chars"],
            "output_text": row["output_text"], "error_message": row["error_message"],
            "prompt_tokens": row["prompt_tokens"], "output_tokens": row["output_tokens"],
            "duration_ms": row["duration_ms"], "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def start_agent_run(self, plan_id: str, fingerprint: str, model: str, prompt_chars: int) -> dict[str, Any]:
        now = utc_now()
        run_id = str(uuid.uuid4())
        with closing(self._connect()) as db, db:
            plan = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
            if plan is None:
                raise StoreError("PLAN_NOT_FOUND", "طرح پیدا نشد.", 404)
            if plan["fingerprint"] != fingerprint:
                raise StoreError("PLAN_FINGERPRINT_MISMATCH", "ورودی‌ها با Preview تأییدشده مطابقت ندارند؛ Preview تازه بساز.", 409)
            if plan["status"] != "approved":
                raise StoreError("INVALID_PLAN_STATE", "اجرای ایجنت فقط برای طرحی مجاز است که صریحاً تأیید شده باشد.", 409)
            if db.execute("SELECT 1 FROM agent_runs WHERE plan_id = ? AND status = 'running'", (plan_id,)).fetchone():
                raise StoreError("AGENT_ALREADY_RUNNING", "برای این طرح یک اجرای ایجنت در حال انجام است.", 409)
            attempt = db.execute(
                "SELECT COALESCE(MAX(attempt), 0) + 1 AS next_attempt FROM agent_runs WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()["next_attempt"]
            db.execute(
                """INSERT INTO agent_runs
                (id, plan_id, attempt, model, status, prompt_chars, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'running', ?, ?, ?)""",
                (run_id, plan_id, attempt, model, max(0, int(prompt_chars)), now, now),
            )
            self._audit(db, plan["project_id"], plan_id, "agent_run_started", {"attempt": attempt, "model": model}, now)
            row = db.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
        return self._agent_run(row)

    def finish_agent_run(
        self, run_id: str, status: str, output_text: str = "", error_message: str = "",
        prompt_tokens: int = 0, output_tokens: int = 0, duration_ms: int = 0,
    ) -> dict[str, Any]:
        if status not in ("succeeded", "failed"):
            raise StoreError("INVALID_AGENT_STATUS", "وضعیت نهایی ایجنت معتبر نیست.", 400)
        if not isinstance(output_text, str) or len(output_text) > 200_000:
            raise StoreError("INVALID_AGENT_OUTPUT", "اندازه خروجی ایجنت معتبر نیست.", 400)
        error_message = error_message[:1000] if isinstance(error_message, str) else ""
        counts = [v if isinstance(v, int) and 0 <= v <= 10**12 else 0
                  for v in (prompt_tokens, output_tokens, duration_ms)]
        now = utc_now()
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                raise StoreError("AGENT_RUN_NOT_FOUND", "اجرای ایجنت پیدا نشد.", 404)
            if row["status"] != "running":
                raise StoreError("INVALID_AGENT_STATE", "این اجرای ایجنت قبلاً پایان یافته است.", 409)
            db.execute(
                """UPDATE agent_runs SET status = ?, output_text = ?, error_message = ?,
                prompt_tokens = ?, output_tokens = ?, duration_ms = ?, updated_at = ? WHERE id = ?""",
                (status, output_text, error_message, *counts, now, run_id),
            )
            self._audit(db, "default", row["plan_id"], "agent_run_" + status,
                        {"attempt": row["attempt"], "model": row["model"],
                         "prompt_tokens": counts[0], "output_tokens": counts[1]}, now)
            updated = db.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
        return self._agent_run(updated)

    def get_agent_runs(self, plan_id: str) -> list[dict[str, Any]]:
        with closing(self._connect()) as db, db:
            if db.execute("SELECT id FROM plans WHERE id = ?", (plan_id,)).fetchone() is None:
                raise StoreError("PLAN_NOT_FOUND", "طرح پیدا نشد.", 404)
            rows = db.execute("SELECT * FROM agent_runs WHERE plan_id = ? ORDER BY attempt DESC", (plan_id,)).fetchall()
        return [self._agent_run(row) for row in rows]

    def create_plan(self, plan: dict[str, Any], fingerprint: str, project_id: str = "default") -> dict[str, Any]:
        now = utc_now()
        plan_id = str(uuid.uuid4())
        with closing(self._connect()) as db, db:
            project = db.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
            if project is None:
                raise StoreError("PROJECT_NOT_FOUND", "پروژه پیدا نشد.", 404)
            version = db.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS next_version FROM plans WHERE project_id = ?",
                (project_id,),
            ).fetchone()["next_version"]
            db.execute(
                """
                INSERT INTO plans (id, project_id, version, fingerprint, payload_json, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'draft', ?, ?)
                """,
                (plan_id, project_id, version, fingerprint, _json(plan), now, now),
            )
            for index, task in enumerate(plan.get("tasks", []), start=1):
                task_key = str(task.get("id", index))
                db.execute(
                    """
                    INSERT INTO tasks (id, plan_id, task_key, payload_json, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'planned', ?, ?)
                    """,
                    (f"{plan_id}:{task_key}", plan_id, task_key, _json(task), now, now),
                )
            self._audit(db, project_id, plan_id, "plan_created", {"version": version, "task_count": len(plan.get("tasks", []))}, now)
            row = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        return self._plan(row)

    def get_plan(self, plan_id: str) -> dict[str, Any]:
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if row is None:
            raise StoreError("PLAN_NOT_FOUND", "طرح پیدا نشد.", 404)
        return self._plan(row)

    def approve_plan(self, plan_id: str, fingerprint: str) -> dict[str, Any]:
        now = utc_now()
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
            if row is None:
                raise StoreError("PLAN_NOT_FOUND", "طرح پیدا نشد.", 404)
            if row["fingerprint"] != fingerprint:
                raise StoreError("PLAN_FINGERPRINT_MISMATCH", "ورودی‌ها پس از ساخت Preview تغییر کرده‌اند؛ طرح تازه بسازید.", 409)
            if row["status"] != "draft":
                raise StoreError("INVALID_PLAN_STATE", "فقط طرح پیش‌نویس قابل تأیید است.", 409)
            db.execute("UPDATE plans SET status = 'approved', updated_at = ? WHERE id = ?", (now, plan_id))
            self._audit(db, row["project_id"], plan_id, "plan_approved", {"version": row["version"]}, now)
            updated = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        return self._plan(updated)

    def mark_simulated(self, plan_id: str) -> dict[str, Any]:
        now = utc_now()
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
            if row is None:
                raise StoreError("PLAN_NOT_FOUND", "طرح پیدا نشد.", 404)
            if row["status"] != "approved":
                raise StoreError("INVALID_PLAN_STATE", "برای ثبت شبیه‌سازی، طرح باید قبلاً تأیید شده باشد.", 409)
            db.execute("UPDATE plans SET status = 'simulated', updated_at = ? WHERE id = ?", (now, plan_id))
            db.execute(
                "UPDATE tasks SET status = 'simulated', updated_at = ? WHERE plan_id = ? AND status = 'planned'",
                (now, plan_id),
            )
            self._audit(db, row["project_id"], plan_id, "simulation_completed", {"real_execution": False}, now)
            updated = db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        return self._plan(updated)

    def list_events(self, project_id: str = "default", limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        with closing(self._connect()) as db, db:
            rows = db.execute(
                """
                SELECT id, plan_id, event_type, payload_json, created_at
                FROM audit_events WHERE project_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "plan_id": row["plan_id"],
                "event_type": row["event_type"],
                "details": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    @staticmethod
    def _audit(
        db: sqlite3.Connection,
        project_id: str,
        plan_id: str | None,
        event_type: str,
        details: dict[str, Any],
        created_at: str,
    ) -> None:
        db.execute(
            """
            INSERT INTO audit_events (project_id, plan_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, plan_id, event_type, _json(details), created_at),
        )
