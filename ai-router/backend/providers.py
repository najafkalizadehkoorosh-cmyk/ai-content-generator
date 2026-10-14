"""Non-invasive local Ollama detection; never downloads or runs a model."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
MAX_RESPONSE_BYTES = 1_000_000


def probe_ollama(timeout: float = 1.5) -> dict[str, Any]:
    """Read local model metadata only. No model generation or external requests."""
    request = urllib.request.Request(
        OLLAMA_TAGS_URL,
        headers={"Accept": "application/json", "User-Agent": "AI-Router-Local-Check/1.0"},
        method="GET",
    )
    # Disable environment proxies so a local-only check never leaves this machine.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            return {
                "provider": "ollama",
                "available": False,
                "endpoint": OLLAMA_TAGS_URL,
                "models": [],
                "checked_at": checked_at,
                "message": "پاسخ سرویس محلی از حد مجاز بزرگ‌تر بود؛ بررسی متوقف شد.",
            }
        payload = json.loads(raw.decode("utf-8"))
        source_models = payload.get("models", []) if isinstance(payload, dict) else []
        if not isinstance(source_models, list):
            source_models = []
        models = []
        for item in source_models[:50]:
            if not isinstance(item, dict):
                continue
            details = item.get("details") if isinstance(item.get("details"), dict) else {}
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            size = item.get("size", 0)
            if not isinstance(size, int) or size < 0:
                size = 0
            models.append({
                "name": name[:160],
                "size_bytes": size,
                "parameter_size": str(details.get("parameter_size", ""))[:40],
                "quantization": str(details.get("quantization_level", ""))[:40],
                "family": str(details.get("family", ""))[:40],
            })
        return {
            "provider": "ollama",
            "available": True,
            "endpoint": OLLAMA_TAGS_URL,
            "model_count": len(models),
            "models": models,
            "checked_at": checked_at,
            "message": "سرویس محلی پاسخ داد؛ این فقط وجود سرویس و فهرست مدل‌ها را بررسی می‌کند.",
            "model_calls": 0,
            "downloads_started": 0,
        }
    except (urllib.error.URLError, TimeoutError, OSError):
        return {
            "provider": "ollama",
            "available": False,
            "endpoint": OLLAMA_TAGS_URL,
            "model_count": 0,
            "models": [],
            "checked_at": checked_at,
            "message": "Ollama در این آدرس پاسخ نداد؛ ممکن است اجرا نباشد یا آدرس/تنظیمات آن متفاوت باشد. چیزی دانلود یا اجرا نشد.",
            "model_calls": 0,
            "downloads_started": 0,
        }
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "provider": "ollama",
            "available": False,
            "endpoint": OLLAMA_TAGS_URL,
            "model_count": 0,
            "models": [],
            "checked_at": checked_at,
            "message": "پاسخ سرویس محلی JSON معتبر نبود؛ اتصال برای استفاده تأیید نمی‌شود.",
            "model_calls": 0,
            "downloads_started": 0,
        }
