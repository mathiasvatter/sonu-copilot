from pathlib import Path
import re
from typing import Optional, Tuple
from enum import Enum

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


class Wildcard(Enum):
    GROUP_NAME = "GroupName"
    INSTRUMENT_NAME = "InstrumentName"
    ARTICULATION = "Articulation"
    DYNAMIC = "Dynamic"
    INTERVAL = "Interval"
    VELO_MIN_MAX = "VeloMin-VeloMax"
    ROOT_KEY = "RootKey"
    IGNORE = "Ignore"
    ROUND_ROBIN = "RoundRobin"
    UP_DOWN = "Up/Down"
    MIC_POSITION = "MicPosition"
    SEMITONES = "Semitones"

    def __str__(self) -> str:
        return self.value

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


def is_root_key_token(token: str) -> bool:
    note_re = re.compile(r"^(?P<note>[A-Ga-g])(?P<accidental>#|b)?(?P<octave>-?\d+)$")
    base = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    m = note_re.match(token)
    if not m:
        return False
    note = m.group("note").upper()
    acc = m.group("accidental")
    try:
        octave = int(m.group("octave"), 10)
    except ValueError:
        return False
    if octave < 0 or octave > 8:
        return False
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
    return 0 <= midi <= 128


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


def is_velocity_token(token: str) -> bool:
    if "-" not in token:
        return False
    velo_table = token.split("-")
    if len(velo_table) != 2:
        return False
    try:
        velo_min = int(velo_table[0], 10)
        velo_max = int(velo_table[1], 10)
    except ValueError:
        return False
    if not (0 <= velo_min <= 127 and 0 <= velo_max <= 127):
        return False
    return velo_min != velo_max


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


def is_dynamic_token(token: str) -> bool:
    dynamics = ["ppp", "pp", "p", "mp", "mf", "f", "ff", "fff"]
    return token in dynamics


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


def is_round_robin_token(token: str) -> bool:
    token_upper = token.upper()
    match = re.fullmatch(r"RR-?(\d+)", token_upper)
    if not match:
        return False
    try:
        int(match.group(1))
    except ValueError:
        return False
    return True

def is_up_do_token(token: str) -> bool:
    token_upper = token.upper()
    # allow UP1 or DO1
    match = re.fullmatch(r"(UP|DO)(\d+)", token_upper)
    if not match:
        return False
    try:
        int(match.group(1))
    except ValueError:
        return False
    return True

def is_semitones_token(token: str) -> bool:
    # allow only a number with optional leading + or -
    match = re.fullmatch(r"[+-]?\d+", token)
    if not match:
        return False
    try:
        int(token)
    except ValueError:
        return False
    return True
