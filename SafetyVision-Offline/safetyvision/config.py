"""Application paths and settings that work both from source and from a packaged Windows build."""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    APP_DIR = Path(sys.executable).resolve().parent
    default_data_root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "SafetyVisionOffline" / "data"
else:
    APP_DIR = Path(__file__).resolve().parent.parent
    default_data_root = APP_DIR / "data"

DATA_DIR = Path(os.environ.get("SAFETYVISION_DATA_DIR", str(default_data_root))).expanduser().resolve()
MODEL_DIR = DATA_DIR / "models"
MODEL_PATH = MODEL_DIR / "best.pt"
EVENTS_DIR = DATA_DIR / "events"
DB_PATH = DATA_DIR / "events.db"
SETTINGS_PATH = DATA_DIR / "settings.json"


def _install_bundled_model() -> None:
    """Copy the model shipped inside the Windows package to a persistent writable folder."""
    if MODEL_PATH.is_file():
        return
    bundled_roots = []
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        bundled_roots.append(Path(frozen_root) / "data" / "models" / "best.pt")
    bundled_roots.append(APP_DIR / "data" / "models" / "best.pt")
    source = next((candidate for candidate in bundled_roots if candidate.is_file()), None)
    if source is not None:
        try:
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, MODEL_PATH)
        except OSError:
            # DetectorWorker will show a clear message if model installation fails.
            pass


_install_bundled_model()

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
