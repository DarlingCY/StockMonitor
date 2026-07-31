from __future__ import annotations

import sys
from pathlib import Path


def icon_path() -> Path | None:
    """Return the app icon path for tray / window use, if present."""
    name = "icon.ico"
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "assets" / name)
        candidates.append(Path(sys.executable).resolve().parent / "assets" / name)
    else:
        # src/stockmonitor/resources.py -> repo root assets/
        candidates.append(Path(__file__).resolve().parents[2] / "assets" / name)
    for path in candidates:
        if path.is_file():
            return path
    return None
