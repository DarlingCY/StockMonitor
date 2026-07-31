from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


APP_NAME = "StockMonitor"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_command() -> str:
    """Return the Run-key command that launches without a console window."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    # Dev / source runs: use pythonw so boot autostart does not flash a console.
    python = Path(sys.executable)
    pythonw = python.with_name("pythonw.exe")
    interpreter = pythonw if pythonw.exists() else python
    return f'"{interpreter}" -m stockmonitor.main'


def _read_command() -> str | None:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
        text = str(value).strip()
        return text or None
    except FileNotFoundError:
        return None
    except Exception as exc:
        logger.warning("Failed to read autostart state: {}", exc)
        return None


def is_enabled() -> bool:
    return _read_command() is not None


def set_enabled(enabled: bool) -> bool:
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as exc:
        logger.warning("Failed to update autostart state: {}", exc)
        return False


def sync_command() -> bool:
    """Rewrite a stale Run entry to the current console-less command.

    Older builds registered the console ``Scripts\\stockmonitor`` entry point,
    which opens a CMD window on boot. Call this on startup when autostart is on.
    """
    current = _read_command()
    if current is None:
        return True
    desired = _get_command()
    if current == desired:
        return True
    logger.info("Migrating autostart command to console-less launch")
    return set_enabled(True)
