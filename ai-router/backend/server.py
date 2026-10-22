"""Loopback-only HTTP API and static UI server. Python standard library only."""
from __future__ import annotations

import json
import mimetypes
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from providers import ProviderError, generate_local_response, probe_ollama
from store import Store, StoreError

APP_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB = APP_DIR / "backend" / "data" / "ai_router.sqlite3"
DB_PATH = Path(os.environ.get("AI_ROUTER_DB", str(DEFAULT_DB))).expanduser()
HOST = "127.0.0.1"
PORT = int(os.environ.get("AI_ROUTER_PORT", "8765"))
MAX_BODY_BYTES = 1_000_000
ALLOWED_STATIC = {
    "/": APP_DIR / "index.html",
    "/index.html": APP_DIR / "index.html",
    "/style.css": APP_DIR / "style.css",
    "/core.js": APP_DIR / "core.js",
    "/app.js": APP_DIR / "app.js",
    "/agent-ui.js": APP_DIR / "agent-ui.js",
}
PLAN_ID_RE = re.compile(r"^/api/plans/([0-9a-f-]{36})(?:/(approve|simulation|execute|runs))?$", re.I)
STORE = Store(DB_PATH)


def validate_plan_payload(data: object) -> tuple[dict, str, str]:
    if not isinstance(data, dict):
        raise StoreError("INVALID_JSON", "بدنه درخواست باید یک شیء JSON باشد.", 400)
    project_id = data.get("project_id", "default")
    if project_id != "default":
        raise StoreError("INVALID_PROJECT", "در این نسخه فقط فضای کاری محلی پیش‌فرض پشتیبانی می‌شود.", 400)
    plan = data.get("plan")
    fingerprint = data.get("fingerprint")
    if not isinstance(plan, dict):
        raise StoreError("INVALID_PLAN", "فیلد plan معتبر نیست.", 400)
    if not isinstance(fingerprint, str) or not fingerprint or len(fingerprint) > 12000:
        raise StoreError("INVALID_FINGERPRINT", "اثر انگشت ورودی معتبر نیست.", 400)
    goal = plan.get("goal")
    title = plan.get("title")
    tasks = plan.get("tasks")
    if not isinstance(goal, str) or not 12 <= len(goal.strip()) <= 20000:
        raise StoreError("INVALID_GOAL", "درخواست باید بین ۱۲ تا ۲۰۰۰۰ نویسه باشد.", 400)
    if not isinstance(title, str) or not title.strip() or len(title) > 240:
        raise StoreError("INVALID_TITLE", "عنوان طرح معتبر نیست.", 400)
    if plan.get("budget") != "zero" or plan.get("costPolicy") != "zero-cost-only":
        raise StoreError("BUDGET_POLICY_REJECTED", "ذخیره/اجرا فقط با سیاست صفرهزینه مجاز است.", 403)
    if plan.get("executionMode") != "simulation-only":
        raise StoreError("EXECUTION_POLICY_REJECTED", "Backend فعلی فقط حالت شبیه‌سازی را می‌پذیرد.", 403)
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 30:
        raise StoreError("INVALID_TASKS", "طرح باید بین ۱ تا ۳۰ Task داشته باشد.", 400)
    seen = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise StoreError("INVALID_TASK", "ساختار یکی از Taskها معتبر نیست.", 400)
        task_id = str(task.get("id", ""))
        name = task.get("name")
        if not task_id or len(task_id) > 100 or task_id in seen:
            raise StoreError("INVALID_TASK_ID", "شناسه Task خالی یا تکراری است.", 400)
        if not isinstance(name, str) or not name.strip() or len(name) > 240:
            raise StoreError("INVALID_TASK_NAME", "نام یکی از Taskها معتبر نیست.", 400)
        seen.add(task_id)
    return plan, fingerprint, project_id


class RouterHandler(BaseHTTPRequestHandler):
    server_version = "AIRouterLocal/0.2"
    sys_version = ""

    def log_message(self, format_string: str, *args) -> None:
        # Avoid writing request bodies or potentially sensitive prompt content to logs.
        print("[AI Router] " + (format_string % args))

    def _request_is_local(self) -> bool:
        expected_hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host", "") not in expected_hosts:
            return False
        origin = self.headers.get("Origin")
        if origin:
            allowed_origins = {
                f"http://127.0.0.1:{self.server.server_port}",
                f"http://localhost:{self.server.server_port}",
            }
            if origin not in allowed_origins:
                return False
        return True

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")

    def _send_json(self, status: int, value: dict) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: int, code: str, message: str) -> None:
        self._send_json(status, {"error": {"code": code, "message": message}})

    def _read_json(self) -> dict:
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            raise StoreError("CONTENT_TYPE_REQUIRED", "Content-Type باید application/json باشد.", 415)
        raw_length = self.headers.get("Content-Length", "")
        try:
            length = int(raw_length)
        except (TypeError, ValueError) as exc:
            raise StoreError("CONTENT_LENGTH_REQUIRED", "Content-Length معتبر لازم است.", 411) from exc
        if length < 0 or length > MAX_BODY_BYTES:
            raise StoreError("BODY_TOO_LARGE", "اندازه درخواست بیشتر از حد مجاز است.", 413)
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StoreError("INVALID_JSON", "بدنه درخواست JSON معتبر نیست.", 400) from exc
        if not isinstance(parsed, dict):
            raise StoreError("INVALID_JSON", "بدنه درخواست باید یک شیء JSON باشد.", 400)
        return parsed

    def do_OPTIONS(self) -> None:
        self._send_error_json(405, "METHOD_NOT_ALLOWED", "درخواست OPTIONS پشتیبانی نمی‌شود.")

    def do_GET(self) -> None:
        if not self._request_is_local():
            self._send_error_json(403, "LOCAL_ONLY", "این سرویس فقط از مبدأ محلی مجاز است.")
            return
        parsed = urlsplit(self.path)
        path = parsed.path

        if path in ALLOWED_STATIC:
            self._serve_static(ALLOWED_STATIC[path])
            return
        if path == "/api/health":
            self._send_json(200, {
                "ok": True,
                "service": "AI Router local backend",
                "storage": "sqlite",
                "ai_connected": False,
                "paid_providers_enabled": False,
            })
            return
        if path == "/api/providers":
            self._send_json(200, {
                "ollama": probe_ollama(),
                "paid_providers_enabled": False,
                "cloud_providers_enabled": False,
            })
            return
        try:
            if path == "/api/workspace":
                self._send_json(200, STORE.get_workspace())
                return
            if path == "/api/events":
                query = parse_qs(parsed.query)
                limit = self._safe_limit(query.get("limit", ["50"])[0], 50, 200)
                self._send_json(200, {"events": STORE.list_events(limit=limit)})
                return
            matched = PLAN_ID_RE.fullmatch(path)
            if matched and matched.group(2) is None:
                self._send_json(200, {"record": STORE.get_plan(matched.group(1))})
                return
            if matched and matched.group(2) == "runs":
                self._send_json(200, {"runs": STORE.get_agent_runs(matched.group(1))})
                return
        except StoreError as exc:
            self._send_error_json(exc.status_code, exc.code, str(exc))
            return
        self._send_error_json(404, "NOT_FOUND", "مسیر پیدا نشد.")

    def do_POST(self) -> None:
        if not self._request_is_local():
            self._send_error_json(403, "LOCAL_ONLY", "این سرویس فقط از مبدأ محلی مجاز است.")
            return
        path = urlsplit(self.path).path
        try:
            if path == "/api/plans":
                body = self._read_json()
                plan, fingerprint, project_id = validate_plan_payload(body)
                record = STORE.create_plan(plan, fingerprint, project_id)
                self._send_json(201, {"record": record})
                return

            matched = PLAN_ID_RE.fullmatch(path)
            if matched:
                plan_id, action = matched.groups()
                body = self._read_json()
                if action == "approve":
                    fingerprint = body.get("fingerprint")
                    if not isinstance(fingerprint, str):
                        raise StoreError("INVALID_FINGERPRINT", "اثر انگشت ورودی ارسال نشده است.", 400)
                    record = STORE.approve_plan(plan_id, fingerprint)
                    self._send_json(200, {"record": record})
                    return
                if action == "simulation":
                    record = STORE.mark_simulated(plan_id)
                    self._send_json(200, {"record": record, "real_execution": False})
                    return
                if action == "execute":
                    fingerprint = body.get("fingerprint")
                    model = body.get("model")
                    if not isinstance(fingerprint, str) or not fingerprint or len(fingerprint) > 12000:
                        raise StoreError("INVALID_FINGERPRINT", "اثر انگشت Preview معتبر نیست.", 400)
                    if not isinstance(model, str) or not model.strip() or len(model) > 160:
                        raise StoreError("INVALID_MODEL", "یک مدل محلی معتبر انتخاب کن.", 400)
                    existing = STORE.get_plan(plan_id)
                    if existing["fingerprint"] != fingerprint:
                        raise StoreError("PLAN_FINGERPRINT_MISMATCH", "ورودی‌ها با Preview تأییدشده مطابقت ندارند؛ Preview تازه بساز.", 409)
                    if existing["status"] != "approved":
                        raise StoreError("INVALID_PLAN_STATE", "اجرای ایجنت فقط پس از تأیید صریح Preview مجاز است.", 409)
                    plan = existing["plan"]
                    if plan.get("budget") != "zero" or plan.get("costPolicy") != "zero-cost-only":
                        raise StoreError("BUDGET_POLICY_REJECTED", "اجرای Provider با سیاست صفرهزینه مجاز نیست.", 403)
                    goal = plan.get("goal")
                    if not isinstance(goal, str) or not 1 <= len(goal) <= 20000:
                        raise StoreError("INVALID_GOAL", "متن درخواست برای اجرای مدل معتبر نیست.", 400)
                    diagnostic = probe_ollama()
                    if not diagnostic.get("available"):
                        raise StoreError("OLLAMA_UNAVAILABLE", "Ollama پاسخ نمی‌دهد؛ هیچ سرویس ابری دیگری فراخوانی نشد.", 503)
                    installed_names = {
                        item.get("name") for item in diagnostic.get("models", [])
                        if isinstance(item, dict) and isinstance(item.get("name"), str)
                    }
                    if model not in installed_names:
                        raise StoreError("MODEL_NOT_INSTALLED", "این مدل در فهرست مدل‌های نصب‌شده نیست؛ چیزی دانلود نشد.", 409)
                    run = STORE.start_agent_run(plan_id, fingerprint, model, len(goal))
                    started = time.monotonic()
                    system_prompt = (
                        "تو یک ایجنت متنی محلی هستی. به زبان درخواست کاربر پاسخ مفید و ساخت‌یافته بده. "
                        "فقط همین پاسخ متنی را تولید کن. وانمود نکن وب‌گردی کرده‌ای، منبع زنده را بررسی کرده‌ای، "
                        "فایلی را باز یا تغییر داده‌ای، کدی را اجرا کرده‌ای، تصویری ساخته‌ای یا کاری بیرون از مدل انجام داده‌ای. "
                        "اگر درخواست به ابزارهای در دسترس‌نبوده نیاز دارد، محدودیت را روشن بگو و یک پیش‌نویس مفید ارائه کن. "
                        "زنجیره استدلال پنهان را افشا نکن؛ نتیجه و توضیح کوتاه ارائه کن."
                    )
                    try:
                        generated = generate_local_response(model, goal, system_prompt=system_prompt, timeout=90.0)
                        response_text = generated.get("response")
                        if not isinstance(response_text, str) or not response_text.strip():
                            raise ProviderError("مدل پاسخ متنی معتبری تولید نکرد.")
                        elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
                        record = STORE.finish_agent_run(
                            run["id"], "succeeded", output_text=response_text,
                            prompt_tokens=generated.get("prompt_tokens", 0),
                            output_tokens=generated.get("output_tokens", 0),
                            duration_ms=generated.get("duration_ms", elapsed_ms) or elapsed_ms,
                        )
                        self._send_json(200, {"record": record, "real_execution": True})
                    except ProviderError as exc:
                        elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
                        record = STORE.finish_agent_run(run["id"], "failed", error_message=str(exc), duration_ms=elapsed_ms)
                        self._send_json(502, {
                            "error": {"code": "MODEL_EXECUTION_FAILED", "message": str(exc)},
                            "record": record, "real_execution": True,
                        })
                    except Exception:
                        elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
                        STORE.finish_agent_run(
                            run["id"], "failed",
                            error_message="خطای داخلی هنگام پردازش پاسخ مدل؛ موفقیت ثبت نشد.",
                            duration_ms=elapsed_ms,
                        )
                        self._send_error_json(500, "AGENT_INTERNAL_ERROR", "خطای داخلی هنگام پردازش پاسخ مدل؛ موفقیت ثبت نشد.")
                    return
            self._send_error_json(404, "NOT_FOUND", "مسیر پیدا نشد.")
        except StoreError as exc:
            self._send_error_json(exc.status_code, exc.code, str(exc))
        except (ValueError, TypeError) as exc:
            self._send_error_json(400, "INVALID_REQUEST", "ساختار درخواست معتبر نیست.")

    def _serve_static(self, file_path: Path) -> None:
        try:
            body = file_path.read_bytes()
        except OSError:
            self._send_error_json(500, "STATIC_FILE_ERROR", "خواندن فایل رابط کاربری ناموفق بود.")
            return
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _safe_limit(value: str, default: int, maximum: int) -> int:
        try:
            return max(1, min(int(value), maximum))
        except (ValueError, TypeError):
            return default


def main() -> None:
    try:
        httpd = ThreadingHTTPServer((HOST, PORT), RouterHandler)
    except OSError as exc:
        raise SystemExit(
            f"سرور روی {HOST}:{PORT} اجرا نشد. شاید پورت اشغال باشد؛ AI_ROUTER_PORT را تغییر دهید. جزئیات: {exc}"
        ) from exc
    httpd.daemon_threads = True
    print(f"AI Router local UI: http://127.0.0.1:{PORT}")
    print(f"SQLite database: {DB_PATH.resolve()}")
    print("AI provider: not connected | paid providers: disabled | bind: loopback only")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nسرور متوقف شد.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
