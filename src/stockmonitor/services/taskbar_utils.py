from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from enum import Enum

from loguru import logger
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QGuiApplication


class TaskbarPosition(Enum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    UNKNOWN = "unknown"


@dataclass
class TaskbarInfo:
    hwnd: int
    left: int
    top: int
    right: int
    bottom: int
    width: int
    height: int
    position: TaskbarPosition
    screen_width: int
    screen_height: int


class TaskbarUtils:
    """Windows taskbar detection and positioning utilities using Win32 API."""

    @staticmethod
    def get_taskbar_info() -> TaskbarInfo | None:
        """Get taskbar window handle, position, and size."""
        try:
            user32 = ctypes.windll.user32

            taskbar_hwnd = user32.FindWindowW("Shell_TrayWnd", None)
            if not taskbar_hwnd:
                logger.warning("Taskbar window not found")
                return None

            rect = wintypes.RECT()
            user32.GetWindowRect(taskbar_hwnd, ctypes.byref(rect))

            screen_width = user32.GetSystemMetrics(0)
            screen_height = user32.GetSystemMetrics(1)

            position = TaskbarPosition.BOTTOM
            if rect.top == 0 and rect.bottom < screen_height:
                position = TaskbarPosition.TOP
            elif rect.left == 0 and rect.right < screen_width:
                position = TaskbarPosition.LEFT
            elif rect.right == screen_width and rect.left > 0:
                position = TaskbarPosition.RIGHT

            return TaskbarInfo(
                hwnd=taskbar_hwnd,
                left=rect.left,
                top=rect.top,
                right=rect.right,
                bottom=rect.bottom,
                width=rect.right - rect.left,
                height=rect.bottom - rect.top,
                position=position,
                screen_width=screen_width,
                screen_height=screen_height,
            )
        except Exception as e:
            logger.warning("Failed to get taskbar info: {}", e)
            return None

    @staticmethod
    def get_taskbar_buttons_area() -> dict | None:
        """Get taskbar buttons area info."""
        try:
            user32 = ctypes.windll.user32

            taskbar_hwnd = user32.FindWindowW("Shell_TrayWnd", None)
            if not taskbar_hwnd:
                return None

            task_list_hwnd = user32.FindWindowExW(
                taskbar_hwnd, None, "MSTaskSwWClass", None
            )
            if not task_list_hwnd:
                reb_band_hwnd = user32.FindWindowExW(
                    taskbar_hwnd, None, "ReBarWindow32", None
                )
                if reb_band_hwnd:
                    task_list_hwnd = user32.FindWindowExW(
                        reb_band_hwnd, None, "MSTaskSwWClass", None
                    )

            if not task_list_hwnd:
                return None

            rect = wintypes.RECT()
            user32.GetWindowRect(task_list_hwnd, ctypes.byref(rect))

            return {
                "hwnd": task_list_hwnd,
                "left": rect.left,
                "top": rect.top,
                "right": rect.right,
                "bottom": rect.bottom,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top,
            }
        except Exception as e:
            logger.warning("Failed to get taskbar buttons area: {}", e)
            return None

    @staticmethod
    def get_system_tray_area() -> dict | None:
        """Get system tray area info."""
        try:
            user32 = ctypes.windll.user32

            taskbar_hwnd = user32.FindWindowW("Shell_TrayWnd", None)
            if not taskbar_hwnd:
                return None

            tray_notify_hwnd = user32.FindWindowExW(
                taskbar_hwnd, None, "TrayNotifyWnd", None
            )
            if not tray_notify_hwnd:
                return None

            rect = wintypes.RECT()
            user32.GetWindowRect(tray_notify_hwnd, ctypes.byref(rect))

            return {
                "hwnd": tray_notify_hwnd,
                "left": rect.left,
                "top": rect.top,
                "right": rect.right,
                "bottom": rect.bottom,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top,
            }
        except Exception as e:
            logger.warning("Failed to get system tray area: {}", e)
            return None

    @staticmethod
    def calculate_optimal_position(
        window_width: int,
        window_height: int,
        margin: int = 0,
        horizontal_align: str = "center",
        vertical_align: str = "bottom",
        horizontal_offset: int = 0,
        vertical_offset: int = 0,
    ) -> dict:
        """Calculate optimal window position based on taskbar position and alignment.

        Uses Qt's screen geometry to ensure consistent coordinate system for
        both calculation and positioning.

        Position is calculated as: availableGeometry.top-left + margin + offset

        Args:
            window_width: Window width in pixels (kept for API compatibility)
            window_height: Window height in pixels (kept for API compatibility)
            margin: Margin from screen edges in pixels
            horizontal_align: Kept for API compatibility, not used for positioning
            vertical_align: Kept for API compatibility, not used for positioning
            horizontal_offset: Additional horizontal offset in pixels
            vertical_offset: Additional vertical offset in pixels

        Returns:
            dict with "x", "y", and "position" keys
        """
        taskbar_info = TaskbarUtils.get_taskbar_info()
        if not taskbar_info:
            logger.warning("No taskbar info, using default position")
            return {"x": margin + horizontal_offset, "y": margin + vertical_offset, "position": "default"}

        # Use Qt to find the screen where taskbar is located
        taskbar_screen = QGuiApplication.screenAt(
            QPoint(
                taskbar_info.left + taskbar_info.width // 2,
                taskbar_info.top + taskbar_info.height // 2,
            )
        )
        if taskbar_screen is None:
            taskbar_screen = QGuiApplication.primaryScreen()
        if taskbar_screen is None:
            logger.warning("No screen found, using default position")
            return {"x": margin + horizontal_offset, "y": margin + vertical_offset, "position": "default"}

        # Use available geometry (excludes taskbar) for positioning
        area = taskbar_screen.availableGeometry()

        logger.info(
            "Taskbar info: pos={}, rect=({},{},{},{}), area=({},{},{},{})",
            taskbar_info.position.value,
            taskbar_info.left,
            taskbar_info.top,
            taskbar_info.right,
            taskbar_info.bottom,
            area.left(),
            area.top(),
            area.width(),
            area.height(),
        )

        # Position: availableGeometry.top-left + margin + offset
        x = area.left() + margin + horizontal_offset
        y = area.top() + margin + vertical_offset
        position_str = "top-left-origin"

        logger.info(
            "Calculated position: x={}, y={}, offset=({},{}), position={}",
            x,
            y,
            horizontal_offset,
            vertical_offset,
            position_str,
        )

        return {"x": int(x), "y": int(y), "position": position_str}

    @staticmethod
    def set_window_pos(
        hwnd: int,
        x: int,
        y: int,
        width: int = 0,
        height: int = 0,
        flags: int = 0x0001 | 0x0004,
    ) -> bool:
        """Set window position using Win32 API.

        Args:
            hwnd: Window handle
            x: New x position
            y: New y position
            width: New width (0 to keep current)
            height: New height (0 to keep current)
            flags: SetWindowPos flags (default: SWP_NOSIZE | SWP_NOZORDER)

        Returns:
            True if successful, False otherwise
        """
        try:
            user32 = ctypes.windll.user32
            SWP_NOZORDER = 0x0004
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010

            if width == 0 and height == 0:
                flags |= SWP_NOSIZE
            if flags & SWP_NOZORDER == 0:
                flags |= SWP_NOZORDER

            result = user32.SetWindowPos(
                hwnd,
                0,
                x,
                y,
                width,
                height,
                flags | SWP_NOACTIVATE,
            )
            return result != 0
        except Exception as e:
            logger.warning("Failed to set window position: {}", e)
            return False
