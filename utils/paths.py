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

import xml.etree.ElementTree as ET

def get_primary_color() -> str:
    # Use primaryColor from the local qt_material theme file if available.
    primary_color = "#d4af37"
    try:
        theme_path = resource_path("themes/dark_gold.xml")
        tree = ET.parse(theme_path)
        for color_el in tree.getroot().iter("color"):
            if color_el.attrib.get("name") == "primaryColor" and color_el.text:
                primary_color = color_el.text.strip()
                break
    except Exception:
        pass
    return primary_color