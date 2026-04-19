from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


APP_NAME = "StockMonitor"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_command() -> str:
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
    else:
        exe_path = str(Path(sys.argv[0]).resolve())
    return f'"{exe_path}"'


def is_enabled() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
        return str(value).strip() == _get_command()
    except FileNotFoundError:
        return False
    except Exception as exc:
        logger.warning("Failed to read autostart state: {}", exc)
        return False


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
