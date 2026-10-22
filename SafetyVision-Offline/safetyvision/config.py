"""Application paths and settings."""
from __future__ import annotations
import json
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("SAFETYVISION_DATA_DIR", APP_DIR / "data")).expanduser().resolve()
MODEL_DIR = DATA_DIR / "models"
MODEL_PATH = MODEL_DIR / "best.pt"
EVENTS_DIR = DATA_DIR / "events"
DB_PATH = DATA_DIR / "events.db"
SETTINGS_PATH = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "confidence": 0.45,
    "image_size": 640,
    "event_cooldown_seconds": 5,
    "preview_width": 560,
    "preview_height": 315,
}


def load_settings() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    values = DEFAULT_SETTINGS.copy()
    if SETTINGS_PATH.exists():
        try:
            loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                values.update({k: v for k, v in loaded.items() if k in DEFAULT_SETTINGS})
        except (OSError, json.JSONDecodeError):
            pass
    values["confidence"] = min(0.95, max(0.1, float(values["confidence"])))
    values["image_size"] = int(values["image_size"])
    values["event_cooldown_seconds"] = max(1, int(values["event_cooldown_seconds"]))
    return values


def save_settings(settings: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    merged = DEFAULT_SETTINGS.copy()
    merged.update({k: v for k, v in settings.items() if k in DEFAULT_SETTINGS})
    SETTINGS_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
