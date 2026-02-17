from __future__ import annotations

import os
import wave
from pathlib import Path


def is_wav_silent(file_path: str, chunk_frames: int = 4096) -> bool:
    """
    Return True if a WAV file contains only silence.
    For 8-bit PCM, silence is 0x80. For other PCM widths, silence is 0x00.
    """
    path = Path(file_path)
    if path.suffix.lower() != ".wav":
        raise ValueError(f"Unsupported file type: {path.suffix}")

    with wave.open(str(path), "rb") as wav:
        sample_width = wav.getsampwidth()
        total_frames = wav.getnframes()
        if total_frames == 0:
            return True

        if sample_width == 1:
            silent_byte = b"\x80"
        else:
            silent_byte = b"\x00"

        while True:
            frames = wav.readframes(chunk_frames)
            if not frames:
                break
            if sample_width == 1:
                if any(b != 0x80 for b in frames):
                    return False
            else:
                if any(b != 0x00 for b in frames):
                    return False

    return True


def wav_riff_size_matches_file(file_path: str) -> bool:
    """
    Return True if the RIFF header size matches the actual file size.
    RIFF size should equal (file_size - 8).
    """
    path = Path(file_path)
    if path.suffix.lower() != ".wav":
        raise ValueError(f"Unsupported file type: {path.suffix}")

    file_size = os.path.getsize(path)
    if file_size < 12:
        return False

    with open(path, "rb") as f:
        header = f.read(12)

    if header[:4] != b"RIFF" or header[8:12] != b"WAVE":
        return False

    riff_size = int.from_bytes(header[4:8], byteorder="little", signed=False)
    return riff_size == (file_size - 8)

