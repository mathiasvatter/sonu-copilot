import sys
from pathlib import Path


def resource_path(rel_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    try:
        base_path = Path(sys._MEIPASS)  # type: ignore
    except Exception:
        base_path = Path(__file__).resolve().parent.parent
    return base_path / rel_path


def shorten_path(path: str | Path, num_parents: int) -> Path:
    p = Path(path)
    parts = p.parts

    return Path(*parts[-num_parents:])