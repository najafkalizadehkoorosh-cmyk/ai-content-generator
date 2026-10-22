"""Local model inference and event snapshot saving."""
from __future__ import annotations
import re
import threading
import time
import uuid
from datetime import datetime
import cv2
from PySide6.QtCore import QThread, Signal
from .config import MODEL_PATH
from .policy import violation_label


def safe_stem(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", text).strip("_")[:48] or "camera"


class DetectorWorker(QThread):
    status_changed = Signal(str)
    event_found = Signal(dict)

    def __init__(self, store, settings: dict, parent=None):
        super().__init__(parent)
        self.store = store
        self.settings = dict(settings)
        self._frames = {}
        self._lock = threading.Lock()
        self._last_revision = {}
        self._last_event = {}
        self._confidence = float(settings["confidence"])
        self._cooldown = int(settings["event_cooldown_seconds"])

    def push_frame(self, camera_name: str, frame) -> None:
        with self._lock:
            previous = self._frames.get(camera_name)
            revision = 1 if previous is None else previous[1] + 1
            self._frames[camera_name] = (frame, revision)

    def remove_camera(self, camera_name: str) -> None:
        with self._lock:
            self._frames.pop(camera_name, None)
            self._last_revision.pop(camera_name, None)
        for key in list(self._last_event):
            if key[0] == camera_name:
                self._last_event.pop(key, None)

    def set_confidence(self, value: float) -> None:
        self._confidence = min(0.95, max(0.1, float(value)))

    def run(self):
        if not MODEL_PATH.is_file():
            self.status_changed.emit("مدل پیدا نشد؛ یک‌بار اینترنت را روشن و install_model.bat را اجرا کنید.")
            return
        try:
            from ultralytics import YOLO
            self.status_changed.emit("در حال بارگذاری مدل محلی روی CPU…")
            model = YOLO(str(MODEL_PATH))
            self.status_changed.emit("مدل آماده است؛ تشخیص فقط روی همین رایانه انجام می‌شود.")
        except Exception as exc:
            self.status_changed.emit(f"بارگذاری مدل ناموفق بود: {exc}")
            return

        last_health_ping = time.monotonic()
        while not self.isInterruptionRequested():
            with self._lock:
                work = [(name, frame.copy(), revision)
                        for name, (frame, revision) in self._frames.items()
                        if revision != self._last_revision.get(name, 0)]
            if not work:
                self.msleep(45)
                continue
            for camera_name, frame, revision in work:
                if self.isInterruptionRequested():
                    break
                self._last_revision[camera_name] = revision
                try:
                    result = model.predict(
                        source=frame, imgsz=int(self.settings.get("image_size", 640)),
                        conf=float(self._confidence), device="cpu", verbose=False, max_det=100
                    )[0]
                    candidates = {}
                    if result.boxes is not None:
                        names = result.names
                        for box in result.boxes:
                            class_id = int(box.cls[0].item())
                            class_name = names.get(class_id, str(class_id)) if isinstance(names, dict) else names[class_id]
                            issue = violation_label(str(class_name))
                            score = float(box.conf[0].item())
                            if issue and score >= self._confidence:
                                candidates[issue] = max(score, candidates.get(issue, 0.0))
                    if not candidates:
                        continue
                    annotated = result.plot()
                    now = time.monotonic()
                    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
                    for issue, score in candidates.items():
                        key = (camera_name, issue)
                        if now - self._last_event.get(key, -1e9) < self._cooldown:
                            continue
                        self._last_event[key] = now
                        filename = (datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_" +
                                    safe_stem(camera_name) + "_" + safe_stem(issue) + "_" +
                                    uuid.uuid4().hex[:6] + ".jpg")
                        path = self.store.events_dir / filename
                        if not cv2.imwrite(str(path), annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 94]):
                            self.status_changed.emit(f"ذخیره عکس رویداد ناموفق بود: {path.name}")
                            continue
                        event = {
                            "timestamp": stamp, "camera_name": camera_name, "issue": issue,
                            "confidence": round(score, 4), "image_path": str(path)
                        }
                        try:
                            event["id"] = self.store.add(event)
                            self.event_found.emit(event)
                        except Exception as exc:
                            self.status_changed.emit(f"ثبت رویداد در پایگاه داده ناموفق بود: {exc}")
                except Exception as exc:
                    self.status_changed.emit(f"خطای تشخیص در {camera_name}: {exc}")
            if time.monotonic() - last_health_ping > 30:
                self.status_changed.emit("در حال پایش محلی دوربین‌ها…")
                last_health_ping = time.monotonic()
        self.status_changed.emit("پردازش تشخیص متوقف شد.")
