from __future__ import annotations

from dataclasses import dataclass
from typing import List
import os, sys

from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QIcon, QColor, QFont, QFontDatabase
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QProgressBar, QPushButton, QComboBox, QStackedLayout, QSizePolicy, QGraphicsColorizeEffect,
    QTextEdit
)

from pathlib import Path

from components.Threads import AudioFileCheckThread, FileCheckThread
from components.SchemaSettingsDialog import SchemaSettingsDialog
from utils.paths import resource_path, get_primary_color


def place_widget(widget: QWidget, stretch: int, alignment: Qt.AlignmentFlag) -> QWidget:
    """Helper to center/align a widget inside another container."""
    wrapper = QWidget()
    lay = QVBoxLayout(wrapper)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(widget, stretch, alignment)
    return wrapper

@dataclass
class MainWindow(QMainWindow):
    """Minimal DnD window using PySide6.
    - Drop files/folders onto the main area
    - Recursively collects files (filters .DS_Store)
    - Shows a progress view while processing
    """
    drop_panel: QWidget
    progress_widget: QWidget
    progress_label: QLabel
    progress_bar: QProgressBar
    result_widget: QWidget
    result_status: QLabel
    result_text: QTextEdit
    result_copy_btn: QPushButton
    result_btn: QPushButton
    stack: QStackedLayout
    combo: QComboBox
    btn_setup: QPushButton
    all_paths: List[str]

    def set_icon(self):
        icon_candidate = "icons/sonu.icns"
        if sys.platform.startswith("win"):
            icon_candidate = "icons/sonu.ico"
        icon_path = resource_path(icon_candidate)
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def __init__(self):
        super().__init__()
        self.thread = None
        self.threads = []
        self.setWindowTitle("Sonu Co-Pilot")
        print(f"[INFO] Application started from: {resource_path('.')}")

        self.set_icon()
        self.resize(620, 380)
        self.setAcceptDrops(True)

        # --- Central widget & layout
        self.central = QWidget(self)
        self.setCentralWidget(self.central)
        root = QVBoxLayout(self.central)
        root.setContentsMargins(0, 0, 0, 0)

        # --- Drop image / label
        self.drop_panel = QWidget(self)
        self.createDropPanel(self.drop_panel)
        # self.drop_label = QLabel(self)
		# drop_img_path = resource_path("icons/drop-files.png")
		# pm = QPixmap(str(drop_img_path))
		# pm = pm.scaled(480, 480, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
		# self.drop_label.setPixmap(pm)
		# self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		# self.drop_label.setAccessibleDescription(
		#     "Drop your files/folders here to collect them for batch processing."
		# )

        # --- Progress widget
        self.progress_widget = QWidget(self)
        v = QVBoxLayout(self.progress_widget)
        # v.setContentsMargins(20, 10, 20, 10)
        self.progress_label = QLabel("Processing...", self.progress_widget)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar = QProgressBar(self.progress_widget)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # self.progress_bar.setFixedWidth(480)
        v.addWidget(self.progress_label)
        v.addWidget(self.progress_bar)
        self.progress_widget.setFixedWidth(480)

        # --- Result widget
        self.result_widget = QWidget(self)
        r = QVBoxLayout(self.result_widget)
        r.setContentsMargins(20, 10, 20, 10)
        self.result_status = QLabel("", self.result_widget)
        self.result_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_status.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {get_primary_color()};"
        )
        self.result_text = QTextEdit(self.result_widget)
        self.result_text.setReadOnly(True)
        self.result_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setFixedPitch(True)
        # Prefer common monospace fonts if available.
        for family in ("Monaco", "Menlo", "Consolas", "Courier New"):
            if family in QFontDatabase.families():
                mono.setFamily(family)
                print(f"[INFO] Using monospace font: {family}")
                break
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.result_text.setFont(mono)
        # self.result_text.setStyleSheet(
        #     "QTextEdit { background: #111; color: #eaeaea; padding: 10px; }"
        # )
        self.result_copy_btn = QPushButton("Copy Results", self.result_widget)
        self.result_copy_btn.clicked.connect(self.on_copy_results_clicked)
        self.result_btn = QPushButton("Back to Drop", self.result_widget)
        self.result_btn.clicked.connect(self.on_back_to_drop_clicked)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.result_copy_btn, 0, Qt.AlignmentFlag.AlignLeft)
        btn_row.addStretch(1)
        btn_row.addWidget(self.result_btn, 0, Qt.AlignmentFlag.AlignRight)
        r.addWidget(self.result_status)
        r.addWidget(self.result_text)
        r.addLayout(btn_row)

        # --- Stack: [drop area] <-> [progress]
        self.stack = QStackedLayout()
        self.stack.setContentsMargins(20, 0, 20, 10)
        self.stack.addWidget(self.drop_panel)  # index 0
        self.stack.addWidget(place_widget(self.progress_widget, 1, Qt.AlignmentFlag.AlignCenter))  # index 1
        self.stack.addWidget(self.result_widget)
        self.stack.setCurrentIndex(0)
        root.addLayout(self.stack, 1)

        # --- Bottom bar: process mode + setup button (stub)
        bottom = QHBoxLayout()
        bottom.setContentsMargins(20, 0, 20, 10)
        self.combo = QComboBox(self)
        self.combo.addItems(["Filename Check", "Audio File Check"])
        self.combo.setMinimumWidth(280)
        self.btn_setup = QPushButton("Setup", self)
        self.btn_setup.clicked.connect(self.on_setup_clicked)
        self.combo.currentIndexChanged.connect(self.update_setup_button)
        bottom.addWidget(self.combo, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        bottom.addWidget(self.btn_setup, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        root.addLayout(bottom)
        self.update_setup_button()

        # Collected file list
        self.all_paths: List[str] = []
        self.schema_delimiter = "_"
        self.schema_items = [
            "InstrumentName",
            "Articulation",
            "GroupName",
            "Interval",
            "VeloMin-VeloMax",
            "RootKey",
        ]

    @staticmethod
    def createDropPanel(panel: QWidget):
        col = QVBoxLayout(panel)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(4)
        col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Use your SVG here; replace filename if you have a dedicated "drop-files.svg"
        svg_path = resource_path("icons/download-icon.svg")
        drop_svg = QSvgWidget(str(svg_path), panel)
        drop_svg.setStyleSheet("background: transparent; border: none;")
        drop_svg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Let the icon be reasonably large; you can make it responsive (see resizeEvent below)
        drop_svg.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        drop_svg.setFixedSize(100, 100)  # tweak to taste


        primary_color = get_primary_color()
        drop_caption = QLabel("Drop files or folders here", panel)
        drop_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_caption.setAccessibleDescription(
            "Drop your files/folders here to collect them for batch processing."
        )
        # optional styling
        drop_caption.setStyleSheet(f"font-size: 16px; color: {primary_color};")
        effect = QGraphicsColorizeEffect(drop_svg)
        effect.setColor(QColor(primary_color))  # gleiche Farbe wie Caption
        effect.setStrength(1.0)  # 0..1
        drop_svg.setGraphicsEffect(effect)

        col.addWidget(drop_svg, 0, Qt.AlignmentFlag.AlignCenter)
        col.addWidget(drop_caption, 0, Qt.AlignmentFlag.AlignCenter)


    # ---------- Drag & Drop ----------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept when URLs are present."""
        md: QMimeData = event.mimeData()
        if md.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Collect files recursively and switch to progress view."""
        urls = event.mimeData().urls()
        dropped = [Path(u.toLocalFile()) for u in urls]
        self.stack.setCurrentIndex(1)  # show progress
        self.setAcceptDrops(False)  # block new drops during run
        self.progress_label.setText("Processing...")
        self.progress_bar.setValue(0)

        # Collect files (recursively)
        self.all_paths = self.collect_paths(dropped)
        self.progress_bar.setMaximum(len(self.all_paths) if self.all_paths else 1)

        # worker threads
        self.threads = [
            FileCheckThread(
                files=self.all_paths,
                schema=self.schema_items,
                delimiter=self.schema_delimiter,
            ),
            AudioFileCheckThread(files=self.all_paths),
        ]

        self.thread = self.threads[self.combo.currentIndex()]
        self.thread.progress_size_updated.connect(lambda x: self.progress_bar.setMaximum(x))
        self.thread.progress_bar_updated.connect(lambda x: self.progress_bar.setValue(x))
        self.thread.progress_label_updated.connect(lambda text: self.progress_label.setText(text))
        self.thread.results_ready.connect(self.on_thread_results)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()


    # ---------- Helpers ----------
    def on_thread_results(self, text: str):
        self.result_text.setPlainText(text)
        if "Total issues: 0" in text:
            self.result_status.setText("Congratulations! You're good to go! 🎉")
        else:
            self.result_status.setText("You Fucked up! 😱")
        self.stack.setCurrentIndex(2)

    def on_thread_finished(self):
        self.progress_label.setText("Done.")

    def on_back_to_drop_clicked(self):
        self.result_text.clear()
        self.stack.setCurrentIndex(0)
        self.setAcceptDrops(True)

    def on_copy_results_clicked(self):
        text = self.result_text.toPlainText()
        if not text:
            return
        QApplication.clipboard().setText(text)

    def collect_paths(self, inputs: List[Path]) -> List[str]:
        """Recursively collect files from dropped files/folders.
        Skips .DS_Store and non-existent paths.
        """
        out: List[str] = []
        for p in inputs:
            if not p.exists():
                continue
            if p.is_dir():
                for root, _dirs, files in os.walk(p):
                    for f in files:
                        if f == ".DS_Store":
                            continue
                        out.append(str(Path(root) / f))
            else:
                if p.name != ".DS_Store":
                    out.append(str(p))
        return out

    def on_setup_clicked(self):
        """Stub for settings dialog of the current mode."""
        mode = self.combo.currentText()
        if mode == "Filename Check":
            dialog = SchemaSettingsDialog(
                delimiter=self.schema_delimiter,
                schema=self.schema_items,
                parent=self,
            )
            if dialog.exec():
                self.schema_delimiter = dialog.get_delimiter()
                self.schema_items = dialog.get_schema()
                print("[SETUP] Updated schema:", self.schema_delimiter, self.schema_items)
            return
        return

    def update_setup_button(self):
        mode = self.combo.currentText()
        self.btn_setup.setEnabled(mode == "Filename Check")
