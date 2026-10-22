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


class ProviderError(Exception):
    """Sanitized provider failure safe to show in the local UI."""


MAX_GENERATION_RESPONSE_BYTES = 2_000_000
MAX_PROMPT_CHARS = 20_000
MAX_OUTPUT_CHARS = 200_000


def generate_local_response(
    model: str,
    prompt: str,
    system_prompt: str = "",
    timeout: float = 90.0,
) -> dict[str, Any]:
    """Generate one text response using an already-installed local Ollama model.

    The caller must verify the exact model name against probe_ollama() first.
    This function never downloads models, calls cloud providers, or uses tools.
    """
    if not isinstance(model, str) or not model.strip() or len(model) > 160:
        raise ProviderError("نام مدل محلی معتبر نیست.")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT_CHARS:
        raise ProviderError("متن درخواست خالی است یا از سقف ۲۰۰۰۰ نویسه بیشتر است.")
    if not isinstance(system_prompt, str) or len(system_prompt) > 8_000:
        raise ProviderError("دستور داخلی مدل معتبر نیست.")
    try:
        request_timeout = max(1.0, min(float(timeout), 120.0))
    except (TypeError, ValueError):
        request_timeout = 90.0

    messages = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 1200},
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "AI-Router-Local-Agent/1.0",
        },
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=request_timeout) as response:
            raw = response.read(MAX_GENERATION_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"Ollama API پاسخ HTTP {exc.code} داد؛ اجرای مدل کامل نشد.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ProviderError(
            "اتصال به Ollama برقرار نشد یا زمان اجرای مدل تمام شد؛ وضعیت سرویس و مدل را بررسی کن."
        ) from None

    if len(raw) > MAX_GENERATION_RESPONSE_BYTES:
        raise ProviderError("پاسخ مدل از سقف اندازه مجاز بیشتر بود و ذخیره نشد.")
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ProviderError("Ollama پاسخ JSON معتبر برنگرداند.") from None

    message = result.get("message") if isinstance(result, dict) else None
    response_text = message.get("content") if isinstance(message, dict) else None
    if not isinstance(response_text, str) or not response_text.strip():
        raise ProviderError("مدل پاسخ متنی معتبری تولید نکرد.")
    response_text = response_text[:MAX_OUTPUT_CHARS]

    def safe_count(value: object) -> int:
        return value if isinstance(value, int) and 0 <= value <= 10**12 else 0

    duration_ns = safe_count(result.get("total_duration", 0))
    return {
        "model": model,
        "response": response_text,
        "prompt_tokens": safe_count(result.get("prompt_eval_count", 0)),
        "output_tokens": safe_count(result.get("eval_count", 0)),
        "duration_ms": duration_ns // 1_000_000,
        "done": result.get("done") is True,
    }
