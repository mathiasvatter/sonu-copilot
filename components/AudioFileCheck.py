from __future__ import annotations

import os
import wave
from pathlib import Path
import audioop


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


def wav_has_loop_points(file_path: str) -> bool:
    """
    Return True if a WAV file declares loop points in a 'smpl' chunk.
    This checks NumSampleLoops > 0 in the sampler chunk.
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

        # Iterate RIFF chunks
        while True:
            chunk_header = f.read(8)
            if len(chunk_header) < 8:
                break
            chunk_id = chunk_header[:4]
            chunk_size = int.from_bytes(chunk_header[4:8], byteorder="little", signed=False)

            if chunk_id == b"smpl":
                if chunk_size < 36:
                    return False
                smpl_data = f.read(36)
                if len(smpl_data) < 36:
                    return False
                num_loops = int.from_bytes(smpl_data[28:32], byteorder="little", signed=False)
                return num_loops > 0

            # Skip chunk data (plus padding byte if size is odd)
            skip = chunk_size + (chunk_size % 2)
            f.seek(skip, os.SEEK_CUR)

    return False


def _frame_peak_abs(frame_bytes: bytes, sample_width: int, channels: int) -> int:
    """Return the maximum absolute sample value in one PCM frame."""
    if len(frame_bytes) < sample_width * channels:
        return 0

    peak = 0
    for ch in range(channels):
        start = ch * sample_width
        sample = frame_bytes[start:start + sample_width]
        if sample_width == 1:
            # 8-bit PCM is unsigned and centered at 128.
            value = sample[0] - 128
        elif sample_width == 3:
            # 24-bit PCM sign extension.
            sign = b"\xff" if sample[2] & 0x80 else b"\x00"
            value = int.from_bytes(sample + sign, byteorder="little", signed=True)
        else:
            value = int.from_bytes(sample, byteorder="little", signed=True)
        peak = max(peak, abs(value))
    return peak


def wav_has_hard_edges(
    file_path: str,
    zero_threshold_ratio: float = 0.005,
    edge_window_frames: int = 64,
) -> bool:
    """
    Return True if a WAV has no near-zero sample close to start or end.

    This is a simple click-risk check (missing near-zero edge), not a full
    clipping/distortion analysis over the entire file.
    """
    path = Path(file_path)
    if path.suffix.lower() != ".wav":
        raise ValueError(f"Unsupported file type: {path.suffix}")

    with wave.open(str(path), "rb") as wav:
        if wav.getcomptype() != "NONE":
            raise ValueError(f"Unsupported WAV compression: {wav.getcomptype()}")

        sample_width = wav.getsampwidth()
        channels = wav.getnchannels()
        total_frames = wav.getnframes()
        if total_frames == 0:
            return False
        if sample_width not in (1, 2, 3, 4):
            raise ValueError(f"Unsupported sample width: {sample_width}")

        max_amplitude = 127 if sample_width == 1 else (1 << (8 * sample_width - 1)) - 1
        threshold = max(1, int(max_amplitude * max(0.0, zero_threshold_ratio)))
        window = max(1, min(int(edge_window_frames), total_frames))

        start_data = wav.readframes(window)
        wav.setpos(total_frames - window)
        end_data = wav.readframes(window)

        frame_size = sample_width * channels
        start_min_peak = max_amplitude
        end_min_peak = max_amplitude
        for i in range(window):
            s_frame = start_data[i * frame_size:(i + 1) * frame_size]
            e_frame = end_data[i * frame_size:(i + 1) * frame_size]
            start_min_peak = min(start_min_peak, _frame_peak_abs(s_frame, sample_width, channels))
            end_min_peak = min(end_min_peak, _frame_peak_abs(e_frame, sample_width, channels))

        no_near_zero_at_start = start_min_peak > threshold
        no_near_zero_at_end = end_min_peak > threshold
        return no_near_zero_at_start or no_near_zero_at_end


def wav_has_clipping(
    file_path: str,
    clip_threshold_ratio: float = 0.999,
    min_clipped_samples: int = 3,
    chunk_frames: int = 4096,
) -> bool:
    """
    Return True if a WAV likely contains digital clipping.

    Clipping is flagged when at least `min_clipped_samples` samples reach
    (or exceed) `clip_threshold_ratio` of full scale.
    """
    path = Path(file_path)
    if path.suffix.lower() != ".wav":
        raise ValueError(f"Unsupported file type: {path.suffix}")

    with wave.open(str(path), "rb") as wav:
        if wav.getcomptype() != "NONE":
            raise ValueError(f"Unsupported WAV compression: {wav.getcomptype()}")

        sample_width = wav.getsampwidth()
        channels = wav.getnchannels()
        if sample_width not in (1, 2, 3, 4):
            raise ValueError(f"Unsupported sample width: {sample_width}")
        if channels <= 0:
            return False

        threshold_ratio = min(1.0, max(0.0, clip_threshold_ratio))
        min_hits = max(1, int(min_clipped_samples))
        max_amplitude = 127 if sample_width == 1 else (1 << (8 * sample_width - 1)) - 1
        threshold = max(1, int(max_amplitude * threshold_ratio))

        frame_size = sample_width * channels
        clipped_hits = 0

        while True:
            frames = wav.readframes(chunk_frames)
            if not frames:
                break
            # Fast path: skip whole chunk when no sample gets close to threshold.
            if sample_width == 1:
                signed_frames = audioop.bias(frames, 1, -128)
                chunk_peak = audioop.max(signed_frames, 1)
            else:
                chunk_peak = audioop.max(frames, sample_width)
            if chunk_peak < threshold:
                continue

            frame_count = len(frames) // frame_size

            for i in range(frame_count):
                base = i * frame_size
                for ch in range(channels):
                    start = base + ch * sample_width
                    sample = frames[start:start + sample_width]

                    if sample_width == 1:
                        value = sample[0] - 128
                    elif sample_width == 3:
                        sign = b"\xff" if sample[2] & 0x80 else b"\x00"
                        value = int.from_bytes(sample + sign, byteorder="little", signed=True)
                    else:
                        value = int.from_bytes(sample, byteorder="little", signed=True)

                    if abs(value) >= threshold:
                        clipped_hits += 1
                        if clipped_hits >= min_hits:
                            return True

    return False
