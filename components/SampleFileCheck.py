from pathlib import Path
import re
from typing import Optional, Tuple

_SUFFIX_3DIGIT_RE = re.compile(r"-\d{3}$")


def has_leading_or_trailing_whitespace(filename: str) -> bool:
    """Return True if the filename stem has whitespace at the start or end."""
    stem = Path(filename).stem
    return stem != stem.strip()


def has_dash_3digit_suffix(filename: str) -> bool:
    """Return True if the filename stem ends with -001, -002, -010, etc."""
    stem = Path(filename).stem
    return bool(_SUFFIX_3DIGIT_RE.search(stem))


def split_by_delimiter(filename: str, delimiter: str = "_") -> list[str]:
    """Split the filename stem by the given delimiter and return the parts."""
    stem = Path(filename).stem
    return stem.split(delimiter)

def get_root_key(filename: str, sep: str = "_") -> Optional[int]:
    """
    Searches for a MIDI note token (e.g., C0..C8, C#4, Db3) in filename parts.
    Returns the MIDI note number (0-128) or None.
    """
    parts = split_by_delimiter(filename, sep)
    note_re = re.compile(r"^(?P<note>[A-Ga-g])(?P<accidental>#|b)?(?P<octave>-?\d+)$")
    base = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

    for token in parts:
        m = note_re.match(token)
        if not m:
            continue
        note = m.group("note").upper()
        acc = m.group("accidental")
        try:
            octave = int(m.group("octave"), 10)
        except ValueError:
            continue

        if octave < 0 or octave > 8:
            continue

        semitone = base[note]
        if acc == "#":
            semitone += 1
        elif acc == "b":
            semitone -= 1

        if semitone < 0:
            semitone += 12
            octave -= 1
        elif semitone > 11:
            semitone -= 12
            octave += 1

        midi = (octave + 1) * 12 + semitone
        if 0 <= midi <= 128:
            return midi

    return None


def get_velocity(filename: str, sep: str = "_") -> Optional[Tuple[int, int]]:
    """
    Searches for velocity information in filename.
    Returns (velo_min, velo_max) or None.
    """
    parts = split_by_delimiter(filename, sep)

    for token in parts:
        if "-" in token:
            velo_table = token.split("-")
            if len(velo_table) == 2:
                try:
                    velo_min = int(velo_table[0], 10)
                    velo_max = int(velo_table[1], 10)
                except ValueError:
                    continue

                if velo_min != velo_max:
                    return velo_min, velo_max

    return None


def get_dynamic(filename: str, sep: str = "_") -> Optional[str]:
    """
    Searches for dynamic marking in filename.
    Returns dynamic string or None.
    """
    dynamics = ["ppp", "pp", "p", "mp", "mf", "f", "ff", "fff"]

    parts = split_by_delimiter(filename, sep)

    for dyn in dynamics:
        if dyn in parts:
            return dyn

    return None


def get_round_robin(filename: str, sep: str = "_") -> Optional[int]:
    """
    Searches for round robin information in filename.
    Returns RR index as int or None.
    """
    parts = split_by_delimiter(filename, sep)

    for token in parts:
        token_upper = token.upper()
        if "RR" in token_upper:
            match = re.search(r"RR-?(\d+)", token_upper)
            if match:
                return int(match.group(1))

    return None
