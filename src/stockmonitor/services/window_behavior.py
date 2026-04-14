from __future__ import annotations

from loguru import logger


def apply_windows_extended_styles(hwnd: int, topmost: bool = True) -> None:
    try:
        import win32con
        import win32gui
    except ImportError:
        logger.warning("pywin32 unavailable; skip extended style setup")
        return

    try:
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        ex_style |= win32con.WS_EX_NOACTIVATE
        ex_style |= win32con.WS_EX_TOOLWINDOW
        ex_style &= ~win32con.WS_EX_APPWINDOW
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
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
            | win32con.SWP_FRAMECHANGED,
        )
        logger.info("Applied extended window styles for hwnd={}", hwnd)
    except Exception as exc:
        logger.warning("Failed to apply window styles: {}", exc)
