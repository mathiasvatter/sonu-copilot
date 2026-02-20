import os
from typing import Optional

from PySide6.QtCore import QThread, Signal

from components.AudioFileCheck import (
    is_wav_silent,
    wav_riff_size_matches_file,
    wav_has_loop_points,
)
from components.SampleFileCheck import (
    Wildcard,
    has_dash_3digit_suffix,
    has_leading_or_trailing_whitespace,
    is_dynamic_token,
    is_root_key_token,
    is_round_robin_token,
    is_velocity_token,
    split_by_delimiter, is_semitones_token, is_up_do_token, get_root_key, get_velocity, get_round_robin,
)
from utils.paths import shorten_path


class FileCheckThread(QThread):
    progress_bar_updated = Signal(int)
    progress_label_updated = Signal(str)
    progress_size_updated = Signal(int)
    results_ready = Signal(str)
    summary_ready = Signal(str)

    def __init__(self, files, schema=None, delimiter: str = "_", preset_name: str = "Custom"):
        super().__init__()
        self.files = files
        self.schema = schema or []
        self.delimiter = delimiter
        self.preset_name = preset_name
        self.issues = {
            "Leading/Trailing Whitespace": [],
            "Reaper Suffix": [],
            "Schema Length Mismatch": [],
            "Velocity Format": [],
            "RootKey Format": [],
            "RoundRobin Format": [],
            "Semitones Format": [],
            "Up/Down Format": [],
            "Dynamic Format": [],
        }
        self.summary_text = ""

    def append_issue(self, issue: str, file: str) -> None:
        shortened = shorten_path(file, 2)
        self.issues[issue].append(shortened)

    def run(self):
        self.progress_size_updated.emit(len(self.files))
        progress = 0
        for f in self.files:
            file_name, file_ext = os.path.splitext(f)
            if file_ext.lower() not in [".wav", ".aiff", ".flac"]:
                continue

            has_whitespace = has_leading_or_trailing_whitespace(file_name)
            if has_whitespace:
                self.append_issue("Leading/Trailing Whitespace", f)

            has_reaper_suffix = has_dash_3digit_suffix(file_name)
            if has_reaper_suffix:
                self.append_issue("Reaper Suffix", f)

            parts = split_by_delimiter(file_name, self.delimiter)
            if self.schema:
                if len(parts) != len(self.schema):
                    self.append_issue("Schema Length Mismatch", f)
                else:
                    self._check_schema_parts(parts, f)

            progress += 1
            self.progress_bar_updated.emit(progress)
            self.progress_label_updated.emit(f)

        total_issues = self.total_issues()
        if total_issues == 0:
            self.summary_text = self.build_summary()
        else:
            self.summary_text = ""
        self.summary_ready.emit(self.summary_text)
        self.results_ready.emit(self.results_text())
        print("[INFO] File check complete. Issues found:")
        for issue, files in self.issues.items():
            print(f"  {issue}: {len(files)} files")

    def total_issues(self) -> int:
        return sum(len(files) for files in self.issues.values())

    def results_text(self) -> str:
        lines = ["Filename Check Results:", ""]
        total = 0
        for issue, files in self.issues.items():
            count = len(files)
            total += count
            lines.append(f"{issue}: {count}")
            for f in files:
                lines.append(f"  - {f}")
            # if count > 10:
            #     lines.append("  - ...")
            lines.append("")
        lines.append(f"Total issues: {total}")
        return "\n".join(lines)

    def build_summary(self) -> str:
        self.progress_size_updated.emit(len(self.files))
        self.progress_label_updated.emit("Building filename summary...")
        progress = 0

        instrument_idx = self._schema_index(Wildcard.INSTRUMENT_NAME)
        articulation_idx = self._schema_index(Wildcard.ARTICULATION)
        root_idx = self._schema_index(Wildcard.ROOT_KEY)
        velo_idx = self._schema_index(Wildcard.VELO_MIN_MAX)
        rr_idx = self._schema_index(Wildcard.ROUND_ROBIN)

        instruments = set()
        articulations = set()
        min_root = None
        max_root = None
        velocities = set()
        round_robins = set()

        for f in self.files:
            stem, ext = os.path.splitext(f)
            if ext.lower() not in (".wav", ".aiff", ".flac"):
                continue

            parts = split_by_delimiter(stem, self.delimiter)
            if self.schema and len(parts) != len(self.schema):
                continue

            if instrument_idx is not None:
                instrument_name = parts[instrument_idx].strip()
                instruments.add(instrument_name)

            if articulation_idx is not None:
                articulation = parts[articulation_idx].strip()
                articulations.add(articulation)

            if root_idx is not None:
                midi = get_root_key(parts[root_idx])
                if midi is not None:
                    min_root = midi if min_root is None else min(min_root, midi)
                    max_root = midi if max_root is None else max(max_root, midi)

            if velo_idx is not None:
                velo = get_velocity(parts[velo_idx])
                if velo is not None:
                    velocities.add(velo)

            if rr_idx is not None:
                rr = get_round_robin(parts[rr_idx])
                if rr is not None:
                    round_robins.add(rr)

            progress += 1
            self.progress_bar_updated.emit(progress)
            self.progress_label_updated.emit(f)

        instrument_text = ", ".join(sorted(instruments)) if instruments else "-"
        articulation_text = ", ".join(sorted(articulations)) if articulations else "-"
        range_text = "-"
        if min_root is not None and max_root is not None:
            range_text = f"{min_root}-{max_root} ({self._midi_to_note(min_root)} to {self._midi_to_note(max_root)})"

        return (
            f"Instrument: {instrument_text}\n"
            f"Articulation: {articulation_text}\n"
            f"Type: {self.preset_name}\n"
            f"Range: {range_text}\n"
            f"Dynamic Layers: {len(velocities)}\n"
            f"Round Robins: {len(round_robins)}"
        )

    def _schema_index(self, wildcard: Wildcard) -> Optional[int]:
        try:
            return self.schema.index(wildcard.value)
        except ValueError:
            return None

    @staticmethod
    def _midi_to_note(midi: int) -> str:
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        note = notes[midi % 12]
        octave = (midi // 12) - 1
        return f"{note}{octave}"

    def _check_schema_parts(self, parts, file_path: str) -> None:
        for idx, raw in enumerate(self.schema):
            try:
                wildcard = Wildcard(raw)
            except ValueError:
                continue
            token = parts[idx]

            if wildcard == Wildcard.IGNORE:
                continue
            if wildcard == Wildcard.VELO_MIN_MAX and not is_velocity_token(token):
                self.append_issue("Velocity Format", file_path)
            elif wildcard == Wildcard.ROOT_KEY and not is_root_key_token(token):
                self.append_issue("RootKey Format", file_path)
            elif wildcard == Wildcard.ROUND_ROBIN and not is_round_robin_token(token):
                self.append_issue("RoundRobin Format", file_path)
            elif wildcard == Wildcard.DYNAMIC and not is_dynamic_token(token):
                self.append_issue("Dynamic Format", file_path)
            elif wildcard == Wildcard.SEMITONES and not is_semitones_token(token):
                self.append_issue("Semitones Format", file_path)
            elif wildcard == Wildcard.UP_DOWN and is_up_do_token(token):
                self.append_issue("Up/Down Format", file_path)



class AudioFileCheckThread(QThread):
    progress_bar_updated = Signal(int)
    progress_label_updated = Signal(str)
    progress_size_updated = Signal(int)
    results_ready = Signal(str)

    def __init__(self, files, checks=None):
        super().__init__()
        self.files = files
        self.checks = {
            "is_wav_silent": True,
            "wav_riff_size_matches_file": True,
            "wav_has_loop_points": True,
        }
        if isinstance(checks, dict):
            self.checks.update({k: bool(v) for k, v in checks.items()})
        self.issues = {
            "Silent Audio": [],
            "RIFF Size Mismatch": [],
            "Missing Loop Points": [],
            "Unreadable WAV": [],
        }

    def append_issue(self, issue: str, file: str) -> None:
        self.issues[issue].append(shorten_path(file, 2))

    def run(self):
        self.progress_size_updated.emit(len(self.files))
        progress = 0
        for f in self.files:
            _file_name, file_ext = os.path.splitext(f)
            if file_ext.lower() != ".wav":
                continue

            try:
                if self.checks["is_wav_silent"] and is_wav_silent(f):
                    self.append_issue("Silent Audio", f)
                if self.checks["wav_riff_size_matches_file"] and not wav_riff_size_matches_file(f):
                    self.append_issue("RIFF Size Mismatch", f)
                if self.checks["wav_has_loop_points"] and not wav_has_loop_points(f):
                    self.append_issue("Missing Loop Points", f)
            except Exception:
                self.append_issue("Unreadable WAV", f)

            progress += 1
            self.progress_bar_updated.emit(progress)
            self.progress_label_updated.emit(f)

        self.results_ready.emit(self.results_text())
        print("[INFO] Audio file check complete. Issues found:")
        for issue, files in self.issues.items():
            print(f"  {issue}: {len(files)} files")

    def results_text(self) -> str:
        lines = ["Audio File Check Results:", ""]
        total = 0
        for issue, files in self.issues.items():
            count = len(files)
            total += count
            lines.append(f"{issue}: {count}")
            for f in files:
                lines.append(f"  - {f}")
            # if count > 10:
            #     lines.append("  - ...")
            lines.append("")
        lines.append(f"Total issues: {total}")
        return "\n".join(lines)
