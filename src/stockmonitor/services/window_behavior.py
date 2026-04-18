from __future__ import annotations

import ctypes

from loguru import logger
from PySide6.QtCore import QObject, Signal


EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000


def reassert_topmost(hwnd: int, topmost: bool = True) -> None:
    try:
        import win32con
        import win32gui
    except ImportError:
        logger.warning("pywin32 unavailable; skip topmost reassertion")
        return

    try:
        insert_after = win32con.HWND_TOPMOST if topmost else win32con.HWND_NOTOPMOST
        win32gui.SetWindowPos(
            hwnd,
            insert_after,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE
            | win32con.SWP_NOSIZE
            | win32con.SWP_NOACTIVATE
            | win32con.SWP_SHOWWINDOW,
        )
    except Exception as exc:
        logger.warning("Failed to reassert topmost: {}", exc)


class ForegroundWatchdog(QObject):
    foreground_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._hook = None
        self._callback = None

    def start(self) -> None:
        if self._hook is not None:
            return
        try:
            user32 = ctypes.windll.user32
            WinEventProcType = ctypes.WINFUNCTYPE(
                None,
                ctypes.wintypes.HANDLE,
                ctypes.wintypes.DWORD,
                ctypes.wintypes.HWND,
                ctypes.wintypes.LONG,
                ctypes.wintypes.LONG,
                ctypes.wintypes.DWORD,
                ctypes.wintypes.DWORD,
            )

            def _callback(_hook, event, _hwnd, _id_object, _id_child, _thread, _time):
                if event == EVENT_SYSTEM_FOREGROUND:
                    self.foreground_changed.emit()

            self._callback = WinEventProcType(_callback)
            self._hook = user32.SetWinEventHook(
                EVENT_SYSTEM_FOREGROUND,
                EVENT_SYSTEM_FOREGROUND,
                0,
                self._callback,
                0,
                0,
                WINEVENT_OUTOFCONTEXT,
            )
            if not self._hook:
                self._callback = None
                logger.warning("Failed to install foreground watchdog")
        except Exception as exc:
            self._hook = None
            self._callback = None
            logger.warning("Failed to start foreground watchdog: {}", exc)

    def stop(self) -> None:
        if self._hook is None:
            return
        try:
            ctypes.windll.user32.UnhookWinEvent(self._hook)
        except Exception as exc:
            logger.warning("Failed to stop foreground watchdog: {}", exc)
        finally:
            self._hook = None
            self._callback = None


def apply_windows_extended_styles(hwnd: int, topmost: bool = True) -> None:
    try:
        import win32con
        import win32gui
    except ImportError:
        logger.warning("pywin32 unavailable; skip extended style setup")
        return

    try:
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        ex_style |= win32con.WS_EX_TOOLWINDOW
        ex_style &= ~win32con.WS_EX_APPWINDOW
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
        reassert_topmost(hwnd, topmost)
        win32gui.SetWindowPos(
            hwnd,
            0,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE
            | win32con.SWP_NOSIZE
            | win32con.SWP_NOZORDER
            | win32con.SWP_NOACTIVATE
            | win32con.SWP_FRAMECHANGED,
        )
        logger.info("Applied extended window styles for hwnd={}", hwnd)
    except Exception as exc:
        logger.warning("Failed to apply window styles: {}", exc)
