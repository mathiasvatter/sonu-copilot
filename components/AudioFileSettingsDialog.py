from __future__ import annotations

from typing import Dict

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class AudioFileSettingsDialog(QDialog):
    def __init__(self, checks: Dict[str, bool], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Audio File Check Settings")
        self.setMinimumSize(420, 220)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 10)
        root.setSpacing(12)

        root.addWidget(QLabel("Choose which checks should run:", self))

        self.silent_checkbox = QCheckBox("Detect silent WAV files", self)
        self.silent_checkbox.setChecked(bool(checks.get("is_wav_silent", True)))
        root.addWidget(self.silent_checkbox)

        self.riff_checkbox = QCheckBox("Validate WAV RIFF header size", self)
        self.riff_checkbox.setChecked(bool(checks.get("wav_riff_size_matches_file", True)))
        root.addWidget(self.riff_checkbox)

        self.loop_checkbox = QCheckBox("Require loop points (smpl chunk)", self)
        self.loop_checkbox.setChecked(bool(checks.get("wav_has_loop_points", True)))
        root.addWidget(self.loop_checkbox)

        root.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        cancel_btn = QPushButton("Cancel", self)
        ok_btn = QPushButton("OK", self)
        cancel_btn.clicked.connect(self.reject)
        ok_btn.clicked.connect(self.accept)
        footer.addWidget(cancel_btn)
        footer.addWidget(ok_btn)
        root.addLayout(footer)

    def get_checks(self) -> Dict[str, bool]:
        return {
            "is_wav_silent": self.silent_checkbox.isChecked(),
            "wav_riff_size_matches_file": self.riff_checkbox.isChecked(),
            "wav_has_loop_points": self.loop_checkbox.isChecked(),
        }
