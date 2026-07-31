from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from enum import Enum

from loguru import logger
from PySide6.QtCore import QPoint
from PySide6.QtGui import QGuiApplication


class TaskbarPosition(Enum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    UNKNOWN = "unknown"


@dataclass
class TaskbarInfo:
    left: int
    top: int
    width: int
    height: int
    position: TaskbarPosition


class TaskbarUtils:
    """Windows taskbar detection and positioning utilities using Win32 API."""

    @staticmethod
    def get_taskbar_info() -> TaskbarInfo | None:
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
                left=rect.left,
                top=rect.top,
                width=rect.right - rect.left,
                height=rect.bottom - rect.top,
                position=position,
            )
        except Exception as e:
            logger.warning("Failed to get taskbar info: {}", e)
            return None

    @staticmethod
    def calculate_optimal_position(
        window_width: int,
        window_height: int,
        margin: int = 0,
        horizontal_offset: int = 0,
        vertical_offset: int = 0,
    ) -> dict:
        """Position as availableGeometry.top-left + margin + offset.

        Once the vertical offset would push past the screen bottom, stick to
        the bottom edge instead.
        """
        taskbar_info = TaskbarUtils.get_taskbar_info()
        if not taskbar_info:
            logger.warning("No taskbar info, using default position")
            return {
                "x": margin + horizontal_offset,
                "y": margin + vertical_offset,
                "position": "default",
            }

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
            return {
                "x": margin + horizontal_offset,
                "y": margin + vertical_offset,
                "position": "default",
            }

        area = taskbar_screen.availableGeometry()
        screen_geometry = taskbar_screen.geometry()

        x = area.left() + margin + horizontal_offset
        top_origin_y = area.top() + margin + vertical_offset
        bottom_y = screen_geometry.bottom() + 1 - window_height - margin
        if top_origin_y >= bottom_y:
            return {"x": int(x), "y": int(bottom_y), "position": "bottom-sticky"}
        return {"x": int(x), "y": int(top_origin_y), "position": "top-left-origin"}
