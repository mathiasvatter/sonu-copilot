import os

from PySide6.QtCore import QThread, Signal

from components.SampleFileCheck import (
    has_dash_3digit_suffix,
    has_leading_or_trailing_whitespace,
)


class FileCheckThread(QThread):
    progress_bar_updated = Signal(int)
    progress_label_updated = Signal(str)
    progress_size_updated = Signal(int)
    results_ready = Signal(str)

    def __init__(self, files):
        super().__init__()
        self.files = files
        self.issues = {
            "Leading/Trailing Whitespace": [],
            "Reaper Suffix": [],
        }

    def run(self):
        self.progress_size_updated.emit(len(self.files))
        progress = 0
        for f in self.files:
            file_name, file_ext = os.path.splitext(f)
            if file_ext.lower() not in [".wav", ".aiff", ".flac"]:
                continue

            has_whitespace = has_leading_or_trailing_whitespace(file_name)
            if has_whitespace:
                self.issues["Leading/Trailing Whitespace"].append(f)

            has_reaper_suffix = has_dash_3digit_suffix(file_name)
            if has_reaper_suffix:
                self.issues["Reaper Suffix"].append(f)

            progress += 1
            self.progress_bar_updated.emit(progress)
            self.progress_label_updated.emit(f)

        self.results_ready.emit(self.results_text())
        print("[INFO] File check complete. Issues found:")
        for issue, files in self.issues.items():
            print(f"  {issue}: {len(files)} files")

    def results_text(self) -> str:
        lines = ["Filename Check Results", ""]
        total = 0
        for issue, files in self.issues.items():
            count = len(files)
            total += count
            lines.append(f"{issue}: {count}")
            for f in files[:10]:
                lines.append(f"  - {f}")
            if count > 10:
                lines.append("  - ...")
            lines.append("")
        lines.append(f"Total issues: {total}")
        return "\n".join(lines)
