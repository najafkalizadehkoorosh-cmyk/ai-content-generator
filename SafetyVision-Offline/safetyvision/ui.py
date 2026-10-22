"""Persian RTL desktop UI for multi-camera monitoring and event review."""
from __future__ import annotations
import sys
import cv2
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QScrollArea, QFrame, QSplitter, QInputDialog,
    QMessageBox, QDoubleSpinBox, QDialog, QSizePolicy
)
from .config import DATA_DIR, EVENTS_DIR, load_settings, save_settings
from .database import EventStore
from .camera import CameraWorker
from .detector import DetectorWorker

STYLE = """
QMainWindow,QWidget { background:#10151c; color:#edf2f7; font-family:'Segoe UI','Tahoma'; font-size:10pt; }
QFrame#Panel,QFrame#CameraCard,QFrame#EventCard { background:#19222d; border:1px solid #2a3745; border-radius:12px; }
QLabel#Title { font-size:22pt; font-weight:800; color:#f8fafc; }
QLabel#Muted { color:#9fb0c0; }
QLabel#Status { background:#1f2b37; border-radius:8px; padding:8px; color:#a9f0d1; }
QPushButton { background:#273746; border:1px solid #3b4b5b; border-radius:8px; padding:9px 13px; color:#f8fafc; }
QPushButton:hover { background:#344a5e; }
QPushButton#Primary { background:#0e9f6e; border-color:#0e9f6e; font-weight:700; }
QPushButton#Primary:hover { background:#0b875f; }
QLabel#Preview { background:#0b1016; border:1px dashed #354454; border-radius:8px; }
QScrollArea { border:0; background:transparent; }
QDoubleSpinBox { background:#0e141b; border:1px solid #3b4b5b; border-radius:7px; padding:7px; }
QScrollBar:vertical { background:#121820; width:10px; }
QScrollBar::handle:vertical { background:#3c5062; border-radius:5px; min-height:25px; }
"""


def frame_to_pixmap(frame, max_width: int, max_height: int) -> QPixmap:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, channels = rgb.shape
    image = QImage(rgb.data, w, h, channels * w, QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(image).scaled(max_width, max_height, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)


class CameraCard(QFrame):
    stop_requested = Signal(str)

    def __init__(self, name: str):
        super().__init__()
        self.setObjectName("CameraCard")
        self.camera_name = name
        layout = QVBoxLayout(self)
        title_row = QHBoxLayout()
        self.title = QLabel(name)
        self.title.setStyleSheet("font-weight:700;font-size:12pt")
        self.status = QLabel("در انتظار تصویر")
        self.status.setObjectName("Muted")
        stop = QPushButton("حذف")
        stop.setFixedWidth(62)
        stop.clicked.connect(lambda: self.stop_requested.emit(self.camera_name))
        title_row.addWidget(self.title)
        title_row.addStretch(1)
        title_row.addWidget(self.status)
        title_row.addWidget(stop)
        layout.addLayout(title_row)
        self.preview = QLabel("هنوز تصویری دریافت نشده است")
        self.preview.setObjectName("Preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(180)
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.preview)

    def set_status(self, status: str):
        self.status.setText(status)

    def set_frame(self, frame):
        self.preview.setPixmap(frame_to_pixmap(frame, max(320, self.preview.width()-10),
                                               max(180, self.preview.height()-10)))


class ImageDialog(QDialog):
    def __init__(self, image_path: str, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1000, 720)
        layout = QVBoxLayout(self)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(400, 300)
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            label.setText("فایل عکس پیدا نشد.")
        else:
            label.setPixmap(pixmap.scaled(960, 650, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(label)
        close_button = QPushButton("بستن")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignLeft)


class EventCard(QFrame):
    def __init__(self, event: dict, parent=None):
        super().__init__(parent)
        self.event = event
        self.setObjectName("EventCard")
        outer = QVBoxLayout(self)
        image = QLabel()
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image.setMinimumHeight(120)
        pixmap = QPixmap(str(event.get("image_path", "")))
        if not pixmap.isNull():
            image.setPixmap(pixmap.scaled(300, 165, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))
        else:
            image.setText("عکس موجود نیست")
        outer.addWidget(image)
        issue = QLabel(f"⚠  {event.get('issue','رویداد')}")
        issue.setStyleSheet("color:#ffb6a9;font-weight:800")
        outer.addWidget(issue)
        details = QLabel(f"دوربین: {event.get('camera_name','—')}\nاطمینان مدل: {float(event.get('confidence',0)):.0%}\nزمان: {event.get('timestamp','—')}")
        details.setObjectName("Muted")
        details.setWordWrap(True)
        outer.addWidget(details)
        button = QPushButton("نمایش عکس بزرگ")
        button.clicked.connect(lambda: ImageDialog(str(event.get("image_path", "")),
                                                   f"{event.get('issue','رویداد')} — {event.get('camera_name','')}", self).exec())
        outer.addWidget(button)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SafetyVision Offline | پایش تجهیزات ایمنی")
        self.resize(1370, 860)
        self.setMinimumSize(950, 650)
        self.settings = load_settings()
        self.store = EventStore(DATA_DIR / "events.db", EVENTS_DIR)
        self.cameras: dict[str, CameraWorker] = {}
        self.cards: dict[str, CameraCard] = {}
        self.camera_counter = 1
        self._build_ui()
        self.detector = DetectorWorker(self.store, self.settings, self)
        self.detector.status_changed.connect(self.set_global_status)
        self.detector.event_found.connect(self.add_event)
        self.detector.start()
        for item in reversed(self.store.recent(80)):
            self.add_event(item, update_counter=False)
        self.update_counters()
        # Start the default local webcam so a fresh installation is usable immediately.
        self.add_camera("دوربین 1", "0")

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(18, 16, 18, 16)
        main.setSpacing(12)
        header = QHBoxLayout()
        brand = QVBoxLayout()
        title = QLabel("SafetyVision Offline")
        title.setObjectName("Title")
        subtitle = QLabel("پایش آفلاین ماسک و کلاه ایمنی | پردازش روی همین رایانه")
        subtitle.setObjectName("Muted")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch(1)
        header.addWidget(QLabel("آستانهٔ اطمینان"))
        self.confidence = QDoubleSpinBox()
        self.confidence.setRange(0.10, 0.95)
        self.confidence.setSingleStep(0.05)
        self.confidence.setDecimals(2)
        self.confidence.setValue(float(self.settings["confidence"]))
        self.confidence.valueChanged.connect(self.change_confidence)
        header.addWidget(self.confidence)
        self.add_button = QPushButton("＋ افزودن دوربین")
        self.add_button.setObjectName("Primary")
        self.add_button.clicked.connect(self.add_camera_dialog)
        header.addWidget(self.add_button)
        main.addLayout(header)
        self.status = QLabel("در حال آماده‌سازی…")
        self.status.setObjectName("Status")
        self.status.setWordWrap(True)
        main.addWidget(self.status)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        camera_panel = QFrame()
        camera_panel.setObjectName("Panel")
        camera_layout = QVBoxLayout(camera_panel)
        camera_title_row = QHBoxLayout()
        camera_title = QLabel("دوربین‌ها")
        camera_title.setStyleSheet("font-size:14pt;font-weight:800")
        self.camera_count_label = QLabel("۰ دوربین")
        self.camera_count_label.setObjectName("Muted")
        camera_title_row.addWidget(camera_title)
        camera_title_row.addStretch(1)
        camera_title_row.addWidget(self.camera_count_label)
        camera_layout.addLayout(camera_title_row)
        camera_scroll = QScrollArea()
        camera_scroll.setWidgetResizable(True)
        self.camera_grid_widget = QWidget()
        self.camera_grid = QGridLayout(self.camera_grid_widget)
        self.camera_grid.setSpacing(12)
        self.camera_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        camera_scroll.setWidget(self.camera_grid_widget)
        camera_layout.addWidget(camera_scroll)
        self.empty_camera_label = QLabel("برای شروع، روی «افزودن دوربین» بزنید.\n\nمنبع می‌تواند 0 برای وب‌کم، یا آدرس RTSP دوربین IP باشد.")
        self.empty_camera_label.setObjectName("Muted")
        self.empty_camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_grid.addWidget(self.empty_camera_label, 0, 0, 1, 2)
        splitter.addWidget(camera_panel)

        event_panel = QFrame()
        event_panel.setObjectName("Panel")
        event_layout = QVBoxLayout(event_panel)
        event_head = QHBoxLayout()
        event_title = QLabel("رویدادهای مشکوک")
        event_title.setStyleSheet("font-size:14pt;font-weight:800")
        self.event_count_label = QLabel("۰ رویداد")
        self.event_count_label.setObjectName("Muted")
        event_head.addWidget(event_title)
        event_head.addStretch(1)
        event_head.addWidget(self.event_count_label)
        event_layout.addLayout(event_head)
        hint = QLabel("با کلیک روی هر عکس، تصویر بزرگ‌تر باز می‌شود.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        event_layout.addWidget(hint)
        event_scroll = QScrollArea()
        event_scroll.setWidgetResizable(True)
        self.event_list_widget = QWidget()
        self.event_list = QVBoxLayout(self.event_list_widget)
        self.event_list.setSpacing(10)
        self.event_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        event_scroll.setWidget(self.event_list_widget)
        event_layout.addWidget(event_scroll)
        splitter.addWidget(event_panel)
        splitter.setSizes([830, 420])
        main.addWidget(splitter, 1)
        footer = QLabel("تصاویر و تاریخچه فقط در پوشهٔ data ذخیره می‌شوند؛ این برنامه هیچ تصویر یا رویدادی را آپلود نمی‌کند.")
        footer.setObjectName("Muted")
        footer.setWordWrap(True)
        main.addWidget(footer)

    def set_global_status(self, message: str):
        self.status.setText(message)

    def change_confidence(self, value: float):
        self.settings["confidence"] = value
        save_settings(self.settings)
        if hasattr(self, "detector"):
            self.detector.set_confidence(value)

    def add_camera_dialog(self):
        default_source = "0" if not self.cameras else "rtsp://user:password@192.168.1.100:554/stream1"
        source, ok = QInputDialog.getText(self, "افزودن دوربین",
                                          "شماره وب‌کم (مثلاً 0) یا آدرس RTSP دوربین IP:",
                                          text=default_source)
        if not ok or not source.strip():
            return
        source = source.strip()
        if any(worker.source_text == source for worker in self.cameras.values()):
            QMessageBox.information(self, "منبع تکراری", "این منبع دوربین از قبل اضافه شده است.")
            return
        self.camera_counter += 1
        self.add_camera(f"دوربین {self.camera_counter}", source)

    def add_camera(self, name: str, source: str):
        if self.empty_camera_label is not None:
            self.camera_grid.removeWidget(self.empty_camera_label)
            self.empty_camera_label.deleteLater()
            self.empty_camera_label = None
        card = CameraCard(name)
        card.stop_requested.connect(self.remove_camera)
        self.cards[name] = card
        index = len(self.cards) - 1
        self.camera_grid.addWidget(card, index // 2, index % 2)
        worker = CameraWorker(name, source, self)
        worker.frame_ready.connect(self.on_frame)
        worker.status_changed.connect(self.on_camera_status)
        self.cameras[name] = worker
        worker.start()
        self.update_counters()

    def remove_camera(self, name: str):
        worker = self.cameras.pop(name, None)
        if worker is not None:
            worker.requestInterruption()
            worker.wait(2500)
            worker.deleteLater()
        if hasattr(self, "detector"):
            self.detector.remove_camera(name)
        card = self.cards.pop(name, None)
        if card is not None:
            self.camera_grid.removeWidget(card)
            card.deleteLater()
        for i, current in enumerate(self.cards.values()):
            self.camera_grid.addWidget(current, i // 2, i % 2)
        if not self.cards:
            self.empty_camera_label = QLabel("برای شروع، روی «افزودن دوربین» بزنید.\n\nمنبع می‌تواند 0 برای وب‌کم، یا آدرس RTSP دوربین IP باشد.")
            self.empty_camera_label.setObjectName("Muted")
            self.empty_camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.camera_grid.addWidget(self.empty_camera_label, 0, 0, 1, 2)
        self.update_counters()

    def on_frame(self, name: str, frame):
        card = self.cards.get(name)
        if card is not None:
            card.set_frame(frame)
        if hasattr(self, "detector") and self.detector.isRunning():
            self.detector.push_frame(name, frame)

    def on_camera_status(self, name: str, status: str):
        card = self.cards.get(name)
        if card is not None:
            card.set_status(status)

    def add_event(self, event: dict, update_counter: bool = True):
        self.event_list.insertWidget(0, EventCard(event, self))
        if update_counter:
            self.update_counters()

    def update_counters(self):
        self.camera_count_label.setText(f"{len(self.cameras)} دوربین")
        if hasattr(self, "store"):
            self.event_count_label.setText(f"{self.store.count()} رویداد")

    def closeEvent(self, event):
        for worker in list(self.cameras.values()):
            worker.requestInterruption()
        for worker in list(self.cameras.values()):
            worker.wait(2500)
        if hasattr(self, "detector"):
            self.detector.requestInterruption()
            self.detector.wait(5000)
        save_settings(self.settings)
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    return app.exec()
