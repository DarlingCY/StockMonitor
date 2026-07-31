import unittest

from PySide6.QtCore import QRect

from stockmonitor.services import taskbar_utils as mod
from stockmonitor.services.taskbar_utils import (
    TaskbarInfo,
    TaskbarPosition,
    TaskbarUtils,
)


class _FakeScreen:
    def __init__(self, area: QRect):
        self._area = area

    def availableGeometry(self) -> QRect:
        return self._area

    def geometry(self) -> QRect:
        return self._area


class TaskbarUtilsTests(unittest.TestCase):
    def _patch_screen(
        self,
        area: QRect,
        position: TaskbarPosition,
        thickness: int,
        screen_width: int | None = None,
        screen_height: int | None = None,
    ) -> tuple:
        fake_screen = _FakeScreen(area)
        original_get_taskbar_info = TaskbarUtils.get_taskbar_info
        original_screen_at = mod.QGuiApplication.screenAt
        original_primary_screen = mod.QGuiApplication.primaryScreen

        sw = screen_width if screen_width is not None else area.width()
        sh = screen_height if screen_height is not None else area.height()

        if position == TaskbarPosition.LEFT:
            left, top, width, height = 0, 0, thickness, sh
        elif position == TaskbarPosition.RIGHT:
            left, top, width, height = sw - thickness, 0, thickness, sh
        elif position == TaskbarPosition.TOP:
            left, top, width, height = 0, 0, sw, thickness
        else:
            left, top, width, height = 0, sh - thickness, sw, thickness

        TaskbarUtils.get_taskbar_info = staticmethod(
            lambda: TaskbarInfo(
                left=left,
                top=top,
                width=width,
                height=height,
                position=position,
            )
        )
        mod.QGuiApplication.screenAt = staticmethod(lambda _point: fake_screen)
        mod.QGuiApplication.primaryScreen = staticmethod(lambda: fake_screen)
        return original_get_taskbar_info, original_screen_at, original_primary_screen

    def _restore_screen(self, originals: tuple) -> None:
        original_get_taskbar_info, original_screen_at, original_primary_screen = (
            originals
        )
        TaskbarUtils.get_taskbar_info = original_get_taskbar_info
        mod.QGuiApplication.screenAt = original_screen_at
        mod.QGuiApplication.primaryScreen = original_primary_screen

    def test_positions_use_available_geometry_top_left(self) -> None:
        cases = [
            (QRect(70, 0, 1850, 1080), TaskbarPosition.LEFT, 70, (70, 0)),
            (QRect(0, 0, 1850, 1080), TaskbarPosition.RIGHT, 70, (0, 0)),
            (QRect(0, 0, 1920, 1010), TaskbarPosition.BOTTOM, 70, (0, 0)),
            (QRect(0, 70, 1920, 1010), TaskbarPosition.TOP, 70, (0, 70)),
        ]
        for area, position, thickness, expected in cases:
            with self.subTest(position=position):
                originals = self._patch_screen(
                    area, position, thickness, screen_width=1920, screen_height=1080
                )
                try:
                    result = TaskbarUtils.calculate_optimal_position(
                        window_width=520,
                        window_height=44,
                        margin=0,
                    )
                    self.assertEqual((result["x"], result["y"]), expected)
                finally:
                    self._restore_screen(originals)

    def test_offsets_applied(self) -> None:
        cases = [
            (
                QRect(70, 0, 1850, 1080),
                TaskbarPosition.LEFT,
                100,
                50,
                (170, 50),
            ),
            (
                QRect(0, 0, 1850, 1080),
                TaskbarPosition.RIGHT,
                -30,
                20,
                (-30, 20),
            ),
            (
                QRect(0, 0, 1920, 1010),
                TaskbarPosition.BOTTOM,
                50,
                -30,
                (50, -30),
            ),
            (
                QRect(0, 70, 1920, 1010),
                TaskbarPosition.TOP,
                25,
                15,
                (25, 85),
            ),
        ]
        for area, position, hx, vy, expected in cases:
            with self.subTest(position=position):
                originals = self._patch_screen(
                    area, position, 70, screen_width=1920, screen_height=1080
                )
                try:
                    result = TaskbarUtils.calculate_optimal_position(
                        window_width=520,
                        window_height=44,
                        margin=0,
                        horizontal_offset=hx,
                        vertical_offset=vy,
                    )
                    self.assertEqual((result["x"], result["y"]), expected)
                finally:
                    self._restore_screen(originals)

    def test_no_taskbar_uses_default_position(self) -> None:
        original = TaskbarUtils.get_taskbar_info
        TaskbarUtils.get_taskbar_info = staticmethod(lambda: None)
        try:
            result = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_offset=10,
                vertical_offset=20,
            )
            self.assertEqual(result["x"], 10)
            self.assertEqual(result["y"], 20)
        finally:
            TaskbarUtils.get_taskbar_info = original


if __name__ == "__main__":
    unittest.main()
