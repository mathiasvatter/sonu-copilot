from __future__ import annotations

from dataclasses import dataclass
from typing import List
import os

from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QIcon, QColor
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QProgressBar, QPushButton, QComboBox, QStackedLayout, QSizePolicy, QGraphicsColorizeEffect
)

from pathlib import Path
from utils.paths import resource_path

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
    stack: QStackedLayout
    combo: QComboBox
    btn_setup: QPushButton
    all_paths: List[str]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sonu Co-Pilot")
        print(f"[INFO] Application started from: {resource_path('.')}")
        icon_path = resource_path("icons/icon.icns")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
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
        self.progress_bar.setMinimumWidth(480)
        v.addWidget(self.progress_label)
        v.addWidget(self.progress_bar)

        # --- Stack: [drop area] <-> [progress]
        self.stack = QStackedLayout()
        self.stack.setContentsMargins(10, 0, 10, 0)
        self.stack.addWidget(self.drop_panel)  # index 0
        self.stack.addWidget(place_widget(self.progress_widget, 1, Qt.AlignmentFlag.AlignCenter))  # index 1
        self.stack.setCurrentIndex(0)
        root.addLayout(self.stack, 1)

        # --- Bottom bar: process mode + setup button (stub)
        bottom = QHBoxLayout()
        bottom.setContentsMargins(20, 0, 20, 10)
        self.combo = QComboBox(self)
        self.combo.addItems(["Rename Samples", "Normalize Files", "Detect Samples", "Delete BWF Data"])
        self.combo.setMinimumWidth(280)
        self.btn_setup = QPushButton("Setup", self)
        self.btn_setup.clicked.connect(self.on_setup_clicked)
        bottom.addWidget(self.combo, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        bottom.addWidget(self.btn_setup, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        root.addLayout(bottom)

        # Collected file list
        self.all_paths: List[str] = []

    @staticmethod
    def createDropPanel(panel: QWidget):
        col = QVBoxLayout(panel)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(4)
        col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Use your SVG here; replace filename if you have a dedicated "drop-files.svg"
        svg_path = resource_path("icons/download-icon.svg")
        drop_svg = QSvgWidget(str(svg_path), panel)

        # Let the icon be reasonably large; you can make it responsive (see resizeEvent below)
        drop_svg.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        drop_svg.setFixedSize(100, 100)  # tweak to taste

        drop_caption = QLabel("Drop files or folders here", panel)
        drop_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_caption.setAccessibleDescription(
            "Drop your files/folders here to collect them for batch processing."
        )
        # optional styling
        drop_caption.setStyleSheet("font-size: 16px; color: #666;")
        effect = QGraphicsColorizeEffect(drop_svg)
        effect.setColor(QColor("#666"))  # gleiche Farbe wie Caption
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

        # Here you would start your worker/thread; for demo we just iterate.
        processed = 0
        for _ in self.all_paths:
            processed += 1
            self.progress_bar.setValue(processed)
            # In a real app: yield to event loop or do this in a thread.

        # Demo: Print result and return to drop screen
        print(f"[INFO] Collected {len(self.all_paths)} files:")
        for p in self.all_paths[:5]:
            print("  ", p)
        if len(self.all_paths) > 5:
            print("  ...")

        self.progress_label.setText("Done.")
        # self.stack.setCurrentIndex(0)
        self.setAcceptDrops(True)

    # ---------- Helpers ----------
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
        print(f"[SETUP] Open settings for mode: {mode}")
        # TODO: show the respective settings widget/dialog
