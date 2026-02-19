from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QListWidget,
    QListWidgetItem,
)

from components.SampleFileCheck import Wildcard

WILDCARDS = [wildcard.value for wildcard in Wildcard]

SCHEMA_PRESETS = {
    "Custom": (None, None),
    "Sustain": (
            "_",
            [
                "InstrumentName",
                "Articulation",
                "MicPosition",
                "VeloMin-VeloMax",
                "RoundRobin",
                "RootKey",
            ],
        ),
    "One Shot": (
        "_",
        [
            "InstrumentName",
            "Articulation",
            "MicPosition",
            "VeloMin-VeloMax",
            "RoundRobin",
            "RootKey",
        ],
    ),
    "Transition": (
        "_",
        [
            "InstrumentName",
            "Articulation",
            "MicPosition",
            "Dynamic",
            "Up/Down",
            "RootKey",
        ],
    ),
    "Interval": (
        "_",
        [
            "InstrumentName",
            "Articulation",
            "Semitones",
            "MicPosition",
            "VeloMin-VeloMax",
            "RoundRobin",
            "RootKey",
        ],
    ),
}


class SchemaSettingsDialog(QDialog):
    @staticmethod
    def _qcolor_to_rgba(color: QColor, alpha: float) -> str:
        a = max(0, min(255, int(alpha * 255)))
        return f"rgba({color.red()}, {color.green()}, {color.blue()}, {a})"

    def __init__(self, delimiter: str, schema: List[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("File Schema Settings")
        self.setMinimumSize(520, 360)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 10)

        # Presets row
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:", self))
        self.preset_combo = QComboBox(self)
        self.preset_combo.addItems(SCHEMA_PRESETS.keys())
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        preset_row.addWidget(self.preset_combo, 1)
        root.addLayout(preset_row)

        # Delimiter row
        delim_row = QHBoxLayout()
        delim_row.addWidget(QLabel("Delimiter:", self))
        self.delim_input = QLineEdit(self)
        self.delim_input.setText(delimiter)
        self.delim_input.setMaxLength(5)
        delim_row.addWidget(self.delim_input, 1)
        root.addLayout(delim_row)

        # Rows area (draggable)
        self.rows_list = QListWidget(self)
        self.rows_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.rows_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.rows_list.setSpacing(4)
        self.rows_list.setFrameShape(QListWidget.Shape.NoFrame)
        self.rows_list.setStyleSheet(
            """
            QListWidget {
                border: none;
                background: transparent;
            }
            QListWidget::item {
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background: transparent;
            }
            """
        )
        root.addWidget(self.rows_list, 1)

        # Add row button
        add_row = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Wildcard", self)
        self.add_btn.clicked.connect(self.add_row)
        add_row.addWidget(self.add_btn, 0, Qt.AlignmentFlag.AlignLeft)
        add_row.addStretch(1)
        root.addLayout(add_row)

        # Preview
        root.addWidget(QLabel("Preview:", self))
        self.preview_label = QLabel("", self)
        self.preview_label.setStyleSheet("color: #666;")
        root.addWidget(self.preview_label)
        self.warning_label = QLabel("", self)
        self.warning_label.setStyleSheet("color: #b00020;")
        root.addWidget(self.warning_label)

        # Footer buttons
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.ok_btn = QPushButton("OK", self)
        self.cancel_btn = QPushButton("Cancel", self)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        footer.addWidget(self.cancel_btn)
        footer.addWidget(self.ok_btn)
        root.addLayout(footer)

        if schema:
            for item in schema:
                self.add_row(selected=item)
        else:
            self.add_row(selected="InstrumentName")
            self.add_row(selected="Articulation")
            self.add_row(selected="GroupName")

        self.delim_input.textChanged.connect(self.update_preview)
        self.rows_list.model().rowsMoved.connect(self.update_preview)
        self.rows_list.model().rowsInserted.connect(self.update_preview)
        self.rows_list.model().rowsRemoved.connect(self.update_preview)
        self.update_preview()

    def add_row(self, selected: str | None = None) -> None:
        row = QWidget(self.rows_list)
        row.setObjectName("schemaRow")
        row.setStyleSheet(
            """
            QWidget#schemaRow {
                background: transparent;
                border-radius: 6px;
            }
            """
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0,0,0,0)
        # layout.setSpacing(10)

        combo = QComboBox(row)
        combo.addItems(WILDCARDS)
        if selected and selected in WILDCARDS:
            combo.setCurrentText(selected)
        combo.currentTextChanged.connect(self.update_preview)

        remove_btn = QPushButton(row)
        # remove_btn.setFlat(True)
        # delete_icon_path = resource_path("icons/delete.svg")
        # if delete_icon_path.exists():
        #     remove_btn.setIcon(QIcon(str(delete_icon_path)))
        #     remove_btn.setIconSize(QSize(16, 16))
        #     remove_btn.setFixedSize(20, 20)
        # else:
        remove_btn.setText("Remove")
        item = QListWidgetItem(self.rows_list)
        self.rows_list.addItem(item)
        self.rows_list.setItemWidget(item, row)
        remove_btn.clicked.connect(lambda: self.remove_item(item))

        layout.addWidget(combo, 1)
        layout.addWidget(remove_btn, 0)
        row.setMinimumHeight(32)
        row.adjustSize()
        item.setSizeHint(row.sizeHint())
        self.update_preview()

    def remove_item(self, item: QListWidgetItem) -> None:
        row = self.rows_list.itemWidget(item)
        if row is not None:
            row.setParent(None)
            row.deleteLater()
        self.rows_list.takeItem(self.rows_list.row(item))
        self.update_preview()

    def clear_rows(self) -> None:
        while self.rows_list.count() > 0:
            item = self.rows_list.takeItem(0)
            row = self.rows_list.itemWidget(item)
            if row is not None:
                row.setParent(None)
                row.deleteLater()

    def get_schema(self) -> List[str]:
        items: List[str] = []
        for i in range(self.rows_list.count()):
            item = self.rows_list.item(i)
            row = self.rows_list.itemWidget(item)
            if row is None:
                continue
            combo = row.findChild(QComboBox)
            if combo is None:
                continue
            items.append(combo.currentText())
        return items

    def get_delimiter(self) -> str:
        text = self.delim_input.text()
        return text if text else "_"

    def update_preview(self) -> None:
        delimiter = self.get_delimiter()
        schema = self.get_schema()
        self._sync_preset_combo(delimiter, schema)
        self.preview_label.setText(delimiter.join(schema))
        self._update_validation(schema)

    def apply_preset(self, preset_name: str) -> None:
        preset = SCHEMA_PRESETS.get(preset_name)
        if not preset:
            return
        delimiter, schema = preset
        if delimiter is None or schema is None:
            return
        self.delim_input.setText(delimiter)
        self.clear_rows()
        for item in schema:
            self.add_row(selected=item)
        self.update_preview()

    def _update_validation(self, schema: List[str]) -> None:
        counts = {}
        for item in schema:
            if item == "Ignore":
                continue
            counts[item] = counts.get(item, 0) + 1
        duplicates = [k for k, v in counts.items() if v > 1]
        if duplicates:
            self.warning_label.setText(
                "Duplicates not allowed (except Ignore): " + ", ".join(duplicates)
            )
            self.ok_btn.setEnabled(False)
        else:
            self.warning_label.setText("")
            self.ok_btn.setEnabled(True)

    def _matching_preset_name(self, delimiter: str, schema: List[str]) -> str:
        for name, preset in SCHEMA_PRESETS.items():
            if name == "Custom":
                continue
            preset_delim, preset_schema = preset
            if preset_delim == delimiter and preset_schema == schema:
                return name
        return "Custom"

    def _sync_preset_combo(self, delimiter: str, schema: List[str]) -> None:
        target = self._matching_preset_name(delimiter, schema)
        if self.preset_combo.currentText() == target:
            return
        blocked = self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentText(target)
        self.preset_combo.blockSignals(blocked)
