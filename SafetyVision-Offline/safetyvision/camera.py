"""Camera capture worker for webcams and IP/RTSP streams."""
from __future__ import annotations
import time
import cv2
from PySide6.QtCore import QThread, Signal


def parse_source(value: str):
    source = value.strip()
    if not source:
        raise ValueError("منبع دوربین خالی است")
    return int(source) if source.isdigit() else source


class CameraWorker(QThread):
    frame_ready = Signal(str, object)
    status_changed = Signal(str, str)

    def __init__(self, camera_name: str, source: str, parent=None):
        super().__init__(parent)
        self.camera_name = camera_name
        self.source_text = source
        self.source = parse_source(source)

    def run(self):
        retry_delay = 1.0
        while not self.isInterruptionRequested():
            cap = None
            try:
                if isinstance(self.source, int):
                    cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
                    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 4000)
                    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 4000)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not cap.isOpened():
                    self.status_changed.emit(self.camera_name, "اتصال برقرار نشد؛ تلاش مجدد…")
                    cap.release()
                    cap = None
                    self.msleep(int(retry_delay * 1000))
                    retry_delay = min(8.0, retry_delay * 1.5)
                    continue
                retry_delay = 1.0
                self.status_changed.emit(self.camera_name, "متصل")
                last_emit = 0.0
                while not self.isInterruptionRequested():
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        self.status_changed.emit(self.camera_name, "تصویر قطع شد؛ تلاش مجدد…")
                        break
                    now = time.monotonic()
                    if now - last_emit >= 0.10:
                        self.frame_ready.emit(self.camera_name, frame)
                        last_emit = now
            except Exception as exc:
                self.status_changed.emit(self.camera_name, f"خطا در دریافت تصویر: {exc}")
            finally:
                if cap is not None:
                    cap.release()
            if not self.isInterruptionRequested():
                self.msleep(900)
        self.status_changed.emit(self.camera_name, "متوقف")
