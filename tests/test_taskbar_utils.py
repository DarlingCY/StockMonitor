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
            taskbar_rect = (0, 0, thickness, sh)
        elif position == TaskbarPosition.RIGHT:
            taskbar_rect = (sw - thickness, 0, sw, sh)
        elif position == TaskbarPosition.TOP:
            taskbar_rect = (0, 0, sw, thickness)
        else:  # BOTTOM
            taskbar_rect = (0, sh - thickness, sw, sh)

        TaskbarUtils.get_taskbar_info = staticmethod(
            lambda: TaskbarInfo(
                hwnd=1,
                left=taskbar_rect[0],
                top=taskbar_rect[1],
                right=taskbar_rect[2],
                bottom=taskbar_rect[3],
                width=taskbar_rect[2] - taskbar_rect[0],
                height=taskbar_rect[3] - taskbar_rect[1],
                position=position,
                screen_width=sw,
                screen_height=sh,
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

    def test_left_taskbar_position_uses_available_geometry_top_left(self) -> None:
        """Test that position is based on availableGeometry.top-left for LEFT taskbar."""
        area = QRect(70, 0, 1920 - 70, 1080)  # LEFT taskbar takes 70px from left
        originals = self._patch_screen(
            area,
            TaskbarPosition.LEFT,
            thickness=70,
            screen_width=1920,
            screen_height=1080,
        )
        try:
            result = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_offset=0,
                vertical_offset=0,
            )
            # Position should be: area.left() + margin, area.top() + margin
            # = 70 + 0, 0 + 0 = 70, 0
            self.assertEqual(result["x"], 70)
            self.assertEqual(result["y"], 0)
        finally:
            self._restore_screen(originals)

    def test_right_taskbar_position_uses_available_geometry_top_left(self) -> None:
        """Test that position is based on availableGeometry.top-left for RIGHT taskbar."""
        area = QRect(0, 0, 1920 - 70, 1080)  # RIGHT taskbar takes 70px from right
        originals = self._patch_screen(
            area,
            TaskbarPosition.RIGHT,
            thickness=70,
            screen_width=1920,
            screen_height=1080,
        )
        try:
            result = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_offset=0,
                vertical_offset=0,
            )
            # Position should be: area.left() + margin, area.top() + margin
            # = 0 + 0, 0 + 0 = 0, 0
            self.assertEqual(result["x"], 0)
            self.assertEqual(result["y"], 0)
        finally:
            self._restore_screen(originals)

    def test_bottom_taskbar_position_uses_available_geometry_top_left(self) -> None:
        """Test that position is based on availableGeometry.top-left for BOTTOM taskbar."""
        area = QRect(0, 0, 1920, 1080 - 70)  # BOTTOM taskbar takes 70px from bottom
        fake_screen = _FakeScreen(area)

        original_get_taskbar_info = TaskbarUtils.get_taskbar_info
        original_screen_at = mod.QGuiApplication.screenAt
        original_primary_screen = mod.QGuiApplication.primaryScreen

        TaskbarUtils.get_taskbar_info = staticmethod(
            lambda: TaskbarInfo(
                hwnd=1,
                left=0,
                top=1010,
                right=1920,
                bottom=1080,
                width=1920,
                height=70,
                position=TaskbarPosition.BOTTOM,
                screen_width=1920,
                screen_height=1080,
            )
        )
        mod.QGuiApplication.screenAt = staticmethod(lambda _point: fake_screen)
        mod.QGuiApplication.primaryScreen = staticmethod(lambda: fake_screen)

        try:
            result = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_offset=0,
                vertical_offset=0,
            )
            # Position should be: area.left() + margin, area.top() + margin
            # = 0 + 0, 0 + 0 = 0, 0
            self.assertEqual(result["x"], 0)
            self.assertEqual(result["y"], 0)
        finally:
            TaskbarUtils.get_taskbar_info = original_get_taskbar_info
            mod.QGuiApplication.screenAt = original_screen_at
            mod.QGuiApplication.primaryScreen = original_primary_screen

    def test_top_taskbar_position_uses_available_geometry_top_left(self) -> None:
        """Test that position is based on availableGeometry.top-left for TOP taskbar."""
        area = QRect(0, 70, 1920, 1080 - 70)  # TOP taskbar takes 70px from top
        fake_screen = _FakeScreen(area)

        original_get_taskbar_info = TaskbarUtils.get_taskbar_info
        original_screen_at = mod.QGuiApplication.screenAt
        original_primary_screen = mod.QGuiApplication.primaryScreen

        TaskbarUtils.get_taskbar_info = staticmethod(
            lambda: TaskbarInfo(
                hwnd=1,
                left=0,
                top=0,
                right=1920,
                bottom=70,
                width=1920,
                height=70,
                position=TaskbarPosition.TOP,
                screen_width=1920,
                screen_height=1080,
            )
        )
        mod.QGuiApplication.screenAt = staticmethod(lambda _point: fake_screen)
        mod.QGuiApplication.primaryScreen = staticmethod(lambda: fake_screen)

        try:
            result = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_offset=0,
                vertical_offset=0,
            )
            # Position should be: area.left() + margin, area.top() + margin
            # = 0 + 0, 70 + 0 = 0, 70
            self.assertEqual(result["x"], 0)
            self.assertEqual(result["y"], 70)
        finally:
            TaskbarUtils.get_taskbar_info = original_get_taskbar_info
            mod.QGuiApplication.screenAt = original_screen_at
            mod.QGuiApplication.primaryScreen = original_primary_screen

    def test_left_taskbar_applies_offset(self) -> None:
        """Test that horizontal/vertical offset is applied for LEFT taskbar."""
        area = QRect(70, 0, 1920 - 70, 1080)  # LEFT taskbar takes 70px from left
        originals = self._patch_screen(
            area,
            TaskbarPosition.LEFT,
            thickness=70,
            screen_width=1920,
            screen_height=1080,
        )
        try:
            # Test with positive offsets
            result = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_offset=100,
                vertical_offset=50,
            )
            # Position: area.left() + margin + offset
            # x = 70 + 0 + 100 = 170
            # y = 0 + 0 + 50 = 50
            self.assertEqual(result["x"], 170)
            self.assertEqual(result["y"], 50)

            # Test with negative offsets
            result_neg = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_offset=-20,
                vertical_offset=-10,
            )
            # x = 70 + 0 + (-20) = 50
            # y = 0 + 0 + (-10) = -10
            self.assertEqual(result_neg["x"], 50)
            self.assertEqual(result_neg["y"], -10)
        finally:
            self._restore_screen(originals)

    def test_right_taskbar_applies_offset(self) -> None:
        """Test that horizontal/vertical offset is applied for RIGHT taskbar."""
        area = QRect(0, 0, 1920 - 70, 1080)  # RIGHT taskbar takes 70px from right
        originals = self._patch_screen(
            area,
            TaskbarPosition.RIGHT,
            thickness=70,
            screen_width=1920,
            screen_height=1080,
        )
        try:
            result = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_offset=-30,
                vertical_offset=20,
            )
            # Position: area.left() + margin + offset
            # x = 0 + 0 + (-30) = -30
            # y = 0 + 0 + 20 = 20
            self.assertEqual(result["x"], -30)
            self.assertEqual(result["y"], 20)
        finally:
            self._restore_screen(originals)

    def test_bottom_taskbar_applies_offset(self) -> None:
        """Test that horizontal/vertical offset is applied for BOTTOM taskbar."""
        area = QRect(0, 0, 1920, 1080 - 70)  # BOTTOM taskbar takes 70px from bottom
        fake_screen = _FakeScreen(area)

        original_get_taskbar_info = TaskbarUtils.get_taskbar_info
        original_screen_at = mod.QGuiApplication.screenAt
        original_primary_screen = mod.QGuiApplication.primaryScreen

        TaskbarUtils.get_taskbar_info = staticmethod(
            lambda: TaskbarInfo(
                hwnd=1,
                left=0,
                top=1010,
                right=1920,
                bottom=1080,
                width=1920,
                height=70,
                position=TaskbarPosition.BOTTOM,
                screen_width=1920,
                screen_height=1080,
            )
        )
        mod.QGuiApplication.screenAt = staticmethod(lambda _point: fake_screen)
        mod.QGuiApplication.primaryScreen = staticmethod(lambda: fake_screen)

        try:
            result = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_offset=50,
                vertical_offset=-30,
            )
            # Position: area.left() + margin + offset
            # x = 0 + 0 + 50 = 50
            # y = 0 + 0 + (-30) = -30
            self.assertEqual(result["x"], 50)
            self.assertEqual(result["y"], -30)
        finally:
            TaskbarUtils.get_taskbar_info = original_get_taskbar_info
            mod.QGuiApplication.screenAt = original_screen_at
            mod.QGuiApplication.primaryScreen = original_primary_screen

    def test_top_taskbar_applies_offset(self) -> None:
        """Test that horizontal/vertical offset is applied for TOP taskbar."""
        area = QRect(0, 70, 1920, 1080 - 70)  # TOP taskbar takes 70px from top
        fake_screen = _FakeScreen(area)

        original_get_taskbar_info = TaskbarUtils.get_taskbar_info
        original_screen_at = mod.QGuiApplication.screenAt
        original_primary_screen = mod.QGuiApplication.primaryScreen

        TaskbarUtils.get_taskbar_info = staticmethod(
            lambda: TaskbarInfo(
                hwnd=1,
                left=0,
                top=0,
                right=1920,
                bottom=70,
                width=1920,
                height=70,
                position=TaskbarPosition.TOP,
                screen_width=1920,
                screen_height=1080,
            )
        )
        mod.QGuiApplication.screenAt = staticmethod(lambda _point: fake_screen)
        mod.QGuiApplication.primaryScreen = staticmethod(lambda: fake_screen)

        try:
            result = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_offset=25,
                vertical_offset=15,
            )
            # Position: area.left() + margin + offset
            # x = 0 + 0 + 25 = 25
            # y = 70 + 0 + 15 = 85
            self.assertEqual(result["x"], 25)
            self.assertEqual(result["y"], 85)
        finally:
            TaskbarUtils.get_taskbar_info = original_get_taskbar_info
            mod.QGuiApplication.screenAt = original_screen_at
            mod.QGuiApplication.primaryScreen = original_primary_screen

    def test_no_taskbar_uses_default_position(self) -> None:
        """Test that when no taskbar info is available, default position is used."""
        original_get_taskbar_info = TaskbarUtils.get_taskbar_info
        TaskbarUtils.get_taskbar_info = staticmethod(lambda: None)

        try:
            result = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_offset=10,
                vertical_offset=20,
            )
            # Default position: margin + offset
            # x = 0 + 10 = 10
            # y = 0 + 20 = 20
            self.assertEqual(result["x"], 10)
            self.assertEqual(result["y"], 20)
        finally:
            TaskbarUtils.get_taskbar_info = original_get_taskbar_info

    def test_alignment_params_ignored(self) -> None:
        """Test that horizontal_align and vertical_align params are ignored."""
        area = QRect(70, 0, 1920 - 70, 1080)  # LEFT taskbar
        originals = self._patch_screen(
            area,
            TaskbarPosition.LEFT,
            thickness=70,
            screen_width=1920,
            screen_height=1080,
        )
        try:
            # Test with different alignment values - should all produce same result
            result_left = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_align="left",
                vertical_align="top",
                horizontal_offset=0,
                vertical_offset=0,
            )
            result_center = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_align="center",
                vertical_align="center",
                horizontal_offset=0,
                vertical_offset=0,
            )
            result_right = TaskbarUtils.calculate_optimal_position(
                window_width=520,
                window_height=44,
                margin=0,
                horizontal_align="right",
                vertical_align="bottom",
                horizontal_offset=0,
                vertical_offset=0,
            )

            # All should produce the same position regardless of alignment
            expected_x = 70  # area.left() + margin = 70 + 0
            expected_y = 0   # area.top() + margin = 0 + 0
            self.assertEqual(result_left["x"], expected_x)
            self.assertEqual(result_left["y"], expected_y)
            self.assertEqual(result_center["x"], expected_x)
            self.assertEqual(result_center["y"], expected_y)
            self.assertEqual(result_right["x"], expected_x)
            self.assertEqual(result_right["y"], expected_y)
        finally:
            self._restore_screen(originals)


if __name__ == "__main__":
    unittest.main()
