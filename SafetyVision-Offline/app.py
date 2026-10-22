from __future__ import annotations
import sys, time, sqlite3, threading, re, uuid
from pathlib import Path
from datetime import datetime
import cv2
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QScrollArea, QFrame, QSplitter, QInputDialog,
    QMessageBox, QDoubleSpinBox, QDialog
)

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
MODEL = DATA / "models" / "best.pt"
EVENT_DIR = DATA / "events"
DB = DATA / "events.db"
DATA.mkdir(exist_ok=True)
EVENT_DIR.mkdir(parents=True, exist_ok=True)


def violation_label(name: str):
    name = re.sub(r"[\s_-]+", "", str(name).strip().lower())
    if name in {"nomask", "withoutmask", "maskmissing"}:
        return "ماسک شناسایی نشد"
    if name in {"nohardhat", "nohelmet", "withouthelmet", "helmetmissing", "hardhatmissing"}:
        return "کلاه ایمنی شناسایی نشد"
    return None


class EventStore:
    def __init__(self):
        self.lock = threading.Lock()
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
                camera_name TEXT NOT NULL, issue TEXT NOT NULL,
                confidence REAL NOT NULL, image_path TEXT NOT NULL)""")

    def connect(self):
        db = sqlite3.connect(DB, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def add(self, e):
        with self.lock, self.connect() as db:
            cur = db.execute(
                "INSERT INTO events(timestamp,camera_name,issue,confidence,image_path) VALUES(?,?,?,?,?)",
                (e["timestamp"], e["camera_name"], e["issue"], e["confidence"], e["image_path"])
            )
            return cur.lastrowid

    def recent(self, limit=60):
        with self.lock, self.connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()]

    def count(self):
        with self.lock, self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM events").fetchone()[0]


class CameraWorker(QThread):
    frame_ready = Signal(str, object)
    state = Signal(str, str)

    def __init__(self, name, source):
        super().__init__()
        self.name, self.source_text = name, source.strip()
        self.source = int(source) if source.strip().isdigit() else source.strip()

    def run(self):
        delay = 1
        while not self.isInterruptionRequested():
            cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW) if isinstance(self.source, int) else cv2.VideoCapture(self.source)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not cap.isOpened():
                self.state.emit(self.name, "اتصال برقرار نشد؛ تلاش دوباره…")
                cap.release()
                self.msleep(delay * 1000)
                delay = min(8, delay * 2)
                continue
            delay = 1
            self.state.emit(self.name, "متصل")
            last_emit = 0
            while not self.isInterruptionRequested():
                ok, frame = cap.read()
                if not ok or frame is None:
                    self.state.emit(self.name, "قطع تصویر؛ اتصال مجدد…")
                    break
                now = time.monotonic()
                if now - last_emit >= 0.10:
                    self.frame_ready.emit(self.name, frame)
                    last_emit = now
            cap.release()
            if not self.isInterruptionRequested():
                self.msleep(800)
        self.state.emit(self.name, "متوقف")


class DetectorWorker(QThread):
    state = Signal(str)
    event_found = Signal(dict)

    def __init__(self, store, confidence=0.45, cooldown=5):
        super().__init__()
        self.store, self.confidence, self.cooldown = store, confidence, cooldown
        self.lock = threading.Lock()
        self.frames, self.revisions, self.last_seen = {}, {}, {}
        self.last_alert = {}

    def push(self, name, frame):
        with self.lock:
            self.frames[name] = (frame, self.revisions.get(name, 0) + 1)
            self.revisions[name] = self.revisions.get(name, 0) + 1

    def drop(self, name):
        with self.lock:
            self.frames.pop(name, None)
            self.revisions.pop(name, None)
            self.last_seen.pop(name, None)

    def set_confidence(self, v):
        self.confidence = float(v)

    def run(self):
        if not MODEL.is_file():
            self.state.emit("مدل پیدا نشد؛ یک بار install_model.bat را با اینترنت اجرا کن.")
            return
        try:
            from ultralytics import YOLO
            self.state.emit("در حال بارگذاری مدل محلی روی CPU…")
            model = YOLO(str(MODEL))
            self.state.emit("مدل آماده است؛ پردازش تصویر فقط روی رایانه انجام می‌شود.")
        except Exception as exc:
            self.state.emit(f"خطا در بارگذاری مدل: {exc}")
            return

        while not self.isInterruptionRequested():
            with self.lock:
                todo = [(n, f.copy(), r) for n, (f, r) in self.frames.items()
                        if r != self.last_seen.get(n, 0)]
            if not todo:
                self.msleep(40)
                continue
            for name, frame, revision in todo:
                if self.isInterruptionRequested():
                    break
                self.last_seen[name] = revision
                try:
                    result = model.predict(source=frame, imgsz=640, conf=self.confidence,
                                           device="cpu", verbose=False, max_det=100)[0]
                    found = {}
                    if result.boxes is not None:
                        names = result.names
                        for box in result.boxes:
                            idx = int(box.cls[0].item())
                            cls = names.get(idx, str(idx)) if isinstance(names, dict) else names[idx]
                            issue = violation_label(cls)
                            score = float(box.conf[0].item())
                            if issue and score >= self.confidence:
                                found[issue] = max(score, found.get(issue, 0))
                    if not found:
                        continue
                    painted = result.plot()
                    now = time.monotonic()
                    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
                    for issue, score in found.items():
                        key = (name, issue)
                        if now - self.last_alert.get(key, -1e8) < self.cooldown:
                            continue
                        self.last_alert[key] = now
                        clean_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", name)[:40]
                        image_path = EVENT_DIR / (
                            datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_" +
                            clean_name + "_" + uuid.uuid4().hex[:6] + ".jpg"
                        )
                        if not cv2.imwrite(str(image_path), painted, [int(cv2.IMWRITE_JPEG_QUALITY), 94]):
                            self.state.emit("ذخیرهٔ عکس هشدار ناموفق بود.")
                            continue
                        event = {"timestamp": stamp, "camera_name": name, "issue": issue,
                                 "confidence": round(score, 4), "image_path": str(image_path)}
                        event["id"] = self.store.add(event)
                        self.event_found.emit(event)
                except Exception as exc:
                    self.state.emit(f"خطای تشخیص در {name}: {exc}")


def to_pixmap(frame, w, h):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    hh, ww, ch = rgb.shape
    qimg = QImage(rgb.data, ww, hh, ch * ww, QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(qimg).scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)


class CameraCard(QFrame):
    remove = Signal(str)

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.setStyleSheet("QFrame{background:#19222d;border:1px solid #2a3745;border-radius:10px}")
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        title = QLabel(name)
        title.setStyleSheet("font-weight:bold")
        self.state_label = QLabel("در انتظار تصویر")
        btn = QPushButton("حذف دوربین")
        btn.clicked.connect(lambda: self.remove.emit(self.name))
        row.addWidget(title); row.addStretch(); row.addWidget(self.state_label); row.addWidget(btn)
        layout.addLayout(row)
        self.preview = QLabel("تصویری دریافت نشده")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(180)
        self.preview.setStyleSheet("background:#0b1016;border:1px dashed #354454;border-radius:8px")
        layout.addWidget(self.preview)

    def update_frame(self, frame):
        self.preview.setPixmap(to_pixmap(frame, max(300, self.preview.width()-8),
                                         max(170, self.preview.height()-8)))


class EventCard(QFrame):
    def __init__(self, e, parent=None):
        super().__init__(parent)
        self.e = e
        self.setStyleSheet("QFrame{background:#19222d;border:1px solid #2a3745;border-radius:10px}")
        box = QVBoxLayout(self)
        pic = QLabel()
        pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pm = QPixmap(str(e["image_path"]))
        if not pm.isNull():
            pic.setPixmap(pm.scaled(310, 160, Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation))
        else:
            pic.setText("عکس موجود نیست")
        box.addWidget(pic)
        label = QLabel("⚠ " + e["issue"])
        label.setStyleSheet("color:#ffb6a9;font-weight:bold")
        box.addWidget(label)
        details = QLabel(f"دوربین: {e['camera_name']}\\nاطمینان مدل: {float(e['confidence']):.0%}\\n{e['timestamp']}")
        details.setWordWrap(True)
        details.setStyleSheet("color:#9fb0c0")
        box.addWidget(details)
        btn = QPushButton("نمایش عکس بزرگ")
        btn.clicked.connect(self.show_image)
        box.addWidget(btn)

    def show_image(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.e["issue"])
        dialog.resize(1000, 700)
        layout = QVBoxLayout(dialog)
        pic = QLabel()
        pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = QPixmap(str(self.e["image_path"]))
        if not pix.isNull():
            pic.setPixmap(pix.scaled(950, 620, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        else:
            pic.setText("عکس پیدا نشد.")
        layout.addWidget(pic)
        done = QPushButton("بستن")
        done.clicked.connect(dialog.accept)
        layout.addWidget(done)
        dialog.exec()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SafetyVision Offline | پایش تجهیزات ایمنی")
        self.resize(1350, 850)
        self.store = EventStore()
        self.workers, self.cards, self.counter = {}, {}, 0
        self.setStyleSheet("""
            QMainWindow,QWidget{background:#10151c;color:#edf2f7;font-family:Segoe UI,Tahoma;font-size:10pt}
            QPushButton{background:#273746;border:1px solid #3b4b5b;border-radius:7px;padding:8px 12px}
            QPushButton:hover{background:#344a5e}
            QDoubleSpinBox{background:#19222d;border:1px solid #3b4b5b;border-radius:6px;padding:6px}
            QScrollArea{border:0}
        """)
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        h = QLabel("SafetyVision Offline")
        h.setStyleSheet("font-size:22pt;font-weight:800")
        sub = QLabel("تشخیص آفلاین ماسک و کلاه ایمنی — هشدارها نیازمند بررسی انسانی هستند")
        sub.setStyleSheet("color:#9fb0c0")
        titles.addWidget(h); titles.addWidget(sub)
        header.addLayout(titles); header.addStretch()
        header.addWidget(QLabel("آستانهٔ اعتماد"))
        self.conf = QDoubleSpinBox(); self.conf.setRange(.1,.95); self.conf.setSingleStep(.05)
        self.conf.setValue(.45); self.conf.valueChanged.connect(self.set_conf)
        header.addWidget(self.conf)
        add_btn = QPushButton("＋ افزودن دوربین")
        add_btn.setStyleSheet("background:#0e9f6e;font-weight:bold")
        add_btn.clicked.connect(self.add_camera_dialog)
        header.addWidget(add_btn)
        outer.addLayout(header)
        self.status = QLabel("در حال آماده‌سازی…")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("background:#1f2b37;border-radius:7px;padding:8px;color:#a9f0d1")
        outer.addWidget(self.status)
        split = QSplitter(Qt.Orientation.Horizontal)
        cam_box = QFrame(); cam_layout = QVBoxLayout(cam_box)
        cam_layout.addWidget(QLabel("پیش‌نمایش دوربین‌ها"))
        self.cam_area = QScrollArea(); self.cam_area.setWidgetResizable(True)
        self.cam_root = QWidget(); self.cam_grid = QGridLayout(self.cam_root); self.cam_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cam_area.setWidget(self.cam_root); cam_layout.addWidget(self.cam_area)
        self.empty_label = QLabel("برای شروع، افزودن دوربین را بزنید.\\nوب‌کم: 0  |  دوربین شبکه: آدرس RTSP")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color:#9fb0c0;padding:40px")
        self.cam_grid.addWidget(self.empty_label,0,0,1,2)
        split.addWidget(cam_box)
        events_box = QFrame(); ev_layout = QVBoxLayout(events_box)
        self.event_title = QLabel("عکس هشدارها")
        self.event_title.setStyleSheet("font-size:14pt;font-weight:bold")
        ev_layout.addWidget(self.event_title)
        ev_scroll = QScrollArea(); ev_scroll.setWidgetResizable(True)
        self.ev_root = QWidget(); self.ev_list = QVBoxLayout(self.ev_root); self.ev_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        ev_scroll.setWidget(self.ev_root); ev_layout.addWidget(ev_scroll)
        split.addWidget(events_box); split.setSizes([850,400])
        outer.addWidget(split,1)
        privacy = QLabel("تصاویر و تاریخچه فقط به صورت محلی در پوشهٔ data ذخیره می‌شوند؛ هیچ تصویری آپلود نمی‌شود.")
        privacy.setStyleSheet("color:#9fb0c0")
        outer.addWidget(privacy)
        self.detector = DetectorWorker(self.store)
        self.detector.state.connect(self.status.setText)
        self.detector.event_found.connect(self.add_event)
        self.detector.start()
        for e in reversed(self.store.recent()):
            self.add_event(e, False)
        self.update_event_count()

    def set_conf(self, val):
        if hasattr(self, "detector"):
            self.detector.set_confidence(val)

    def add_camera_dialog(self):
        default = "0" if not self.workers else "rtsp://user:password@192.168.1.100:554/stream1"
        source, ok = QInputDialog.getText(self, "افزودن دوربین", "شمارهٔ وب‌کم (مثل 0) یا آدرس RTSP:", text=default)
        if not ok or not source.strip():
            return
        source = source.strip()
        if any(w.source_text == source for w in self.workers.values()):
            QMessageBox.information(self,"تکراری","این دوربین قبلاً اضافه شده است.")
            return
        self.counter += 1
        name = f"دوربین {self.counter}"
        self.add_camera(name, source)

    def add_camera(self, name, source):
        if self.empty_label is not None:
            self.cam_grid.removeWidget(self.empty_label); self.empty_label.deleteLater(); self.empty_label = None
        card = CameraCard(name); card.remove.connect(self.remove_camera); self.cards[name] = card
        i = len(self.cards)-1; self.cam_grid.addWidget(card,i//2,i%2)
        worker = CameraWorker(name,source)
        worker.frame_ready.connect(self.on_frame); worker.state.connect(self.camera_state)
        self.workers[name] = worker; worker.start()

    def on_frame(self, name, frame):
        if name in self.cards:
            self.cards[name].update_frame(frame)
        if self.detector.isRunning():
            self.detector.push(name, frame)

    def camera_state(self,name,state):
        if name in self.cards:
            self.cards[name].state_label.setText(state)

    def remove_camera(self,name):
        worker = self.workers.pop(name,None)
        if worker:
            worker.requestInterruption(); worker.wait(2500); worker.deleteLater()
        self.detector.drop(name)
        card = self.cards.pop(name,None)
        if card:
            self.cam_grid.removeWidget(card); card.deleteLater()
        for i, card in enumerate(self.cards.values()):
            self.cam_grid.addWidget(card,i//2,i%2)
        if not self.cards and self.empty_label is None:
            self.empty_label = QLabel("برای شروع، افزودن دوربین را بزنید.\\nوب‌کم: 0  |  دوربین شبکه: آدرس RTSP")
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setStyleSheet("color:#9fb0c0;padding:40px")
            self.cam_grid.addWidget(self.empty_label,0,0,1,2)

    def add_event(self,e,update=True):
        self.ev_list.insertWidget(0,EventCard(e,self))
        if update:
            self.update_event_count()

    def update_event_count(self):
        self.event_title.setText(f"عکس هشدارها ({self.store.count()})")

    def closeEvent(self,event):
        for worker in self.workers.values():
            worker.requestInterruption()
        for worker in self.workers.values():
            worker.wait(2500)
        self.detector.requestInterruption(); self.detector.wait(5000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    win = MainWindow(); win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
