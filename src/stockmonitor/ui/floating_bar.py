from __future__ import annotations

from loguru import logger
from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QMouseEvent, QPaintEvent, QPainter
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget

from stockmonitor.models.quote import StockQuote
from stockmonitor.services.taskbar_utils import TaskbarUtils


class FloatingBar(QWidget):
    moved = Signal(int, int)
    keep_visible_requested = Signal()

    def __init__(self, topmost: bool = True, background_color: str = "transparent"):
        super().__init__()
        self.setObjectName("FloatingBar")
        self._keep_visible_enabled = True
        self._corner_radius = 8
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.NoDropShadowWindowHint
        )
        if topmost:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setContentsMargins(0, 0, 0, 0)
        self._logical_width = 0
        self._logical_height = 0
        self.setStyleSheet(
            f"""
            #FloatingBar {{
                color: #f5f5f5;
                font-size: 13px;
            }}
            QLabel {{
                color: #f5f5f5;
                background: transparent;
                border: none;
            }}
            """
        )
        self._drag_offset: QPoint | None = None

        self.label = QLabel("Loading...")
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setMargin(0)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self._sync_size_to_content()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        super().paintEvent(event)

    def _sync_size_to_content(self) -> None:
        previous_pos = self.pos()
        old_height = self.height() or self._logical_height
        screen = self.screen() or QGuiApplication.screenAt(previous_pos) or QGuiApplication.primaryScreen()
        was_bottom_aligned = False
        if screen is not None:
            screen_geometry = screen.geometry()
            old_max_y = screen_geometry.top() + max(0, screen_geometry.height() - old_height)
            was_bottom_aligned = previous_pos.y() >= old_max_y - 1

        content_size = self.sizeHint()
        content_width = content_size.width()
        content_height = content_size.height()
        self._logical_width = content_width
        self._logical_height = content_height
        self.setFixedWidth(content_width)
        self.setFixedHeight(content_height)

        if self.isVisible():
            if screen is not None and was_bottom_aligned:
                screen_geometry = screen.geometry()
                new_y = screen_geometry.bottom() + 1 - self.height()
                clamped_pos = self.clamp_to_work_area(QPoint(previous_pos.x(), new_y))
            else:
                clamped_pos = self.clamp_to_work_area(previous_pos)
            if clamped_pos != previous_pos:
                self.move(clamped_pos)

    def clamp_to_work_area(self, pos: QPoint) -> QPoint:
        # Prefer the live widget size. Using frameGeometry here can keep a stale,
        # larger top-level height and leave a visible gap from the bottom edge.
        win_width = self.width() or self._logical_width
        win_height = self.height() or self._logical_height

        # Get the screen where the window is currently located
        current_screen = self.screen()
        if current_screen is None:
            current_screen = QGuiApplication.primaryScreen()
        if current_screen is None:
            return pos

        # Try to find screen at the new position
        screen = QGuiApplication.screenAt(pos)
        if screen is None:
            # If position is outside all screens, use the current screen
            screen = current_screen

        area = screen.availableGeometry()
        screen_geometry = screen.geometry()

        # Horizontal still respects available work area so it won't overlap
        # left/right taskbar. Vertical uses full screen geometry so the window
        # can move into top/bottom taskbar space when needed.
        min_x = area.left()
        max_x = area.left() + max(0, area.width() - win_width)
        min_y = screen_geometry.top()
        max_y = screen_geometry.top() + max(0, screen_geometry.height() - win_height)

        x = max(min_x, min(pos.x(), max_x))
        y = max(min_y, min(pos.y(), max_y))

        logger.info(
            "clamp_to_work_area: input={}, screen={}, area={}, logical=({},{}), min=({},{}), max=({},{}), output={}",
            (pos.x(), pos.y()),
            screen.geometry().getRect(),
            area.getRect(),
            win_width,
            win_height,
            min_x,
            min_y,
            max_x,
            max_y,
            (x, y),
        )
        return QPoint(x, y)

    def clamp_offset_to_screen(self, offset: QPoint) -> QPoint:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return offset

        area = screen.availableGeometry()
        screen_geometry = screen.geometry()
        width = self.width() or self._logical_width
        height = self.height() or self._logical_height
        max_x = max(0, area.width() - width)
        max_y = max(0, screen_geometry.height() - height)
        x = max(0, min(offset.x(), max_x))
        y = max(0, min(offset.y(), max_y))
        return QPoint(x, y)

    def anchor_to_global(
        self,
        horizontal_align: str = "",
        vertical_align: str = "",
        horizontal_offset: int = 0,
        vertical_offset: int = 0,
    ) -> QPoint:
        """Calculate optimal position based on taskbar position and alignment.

        Uses Win32 API to detect taskbar position and calculates the optimal
        window position based on the specified horizontal and vertical alignment.
        Uses the pre-set widget dimensions (_logical_width, _logical_height)
        to avoid frameGeometry timing issues.

        Position is calculated as: availableGeometry.top-left + margin + offset

        Args:
            horizontal_align: Kept for API compatibility, not used for positioning
            vertical_align: Kept for API compatibility, not used for positioning
            horizontal_offset: Additional horizontal offset in pixels (positive = right)
            vertical_offset: Additional vertical offset in pixels (positive = down)
        """
        position_info = TaskbarUtils.calculate_optimal_position(
            window_width=self._logical_width,
            window_height=self._logical_height,
            margin=0,
            horizontal_align=horizontal_align,
            vertical_align=vertical_align,
            horizontal_offset=horizontal_offset,
            vertical_offset=vertical_offset,
        )

        x = position_info["x"]
        y = position_info["y"]

        logger.info(
            "Anchor position computed: offset=({}, {}), logical=({},{}), target=({}, {}), position={}",
            horizontal_offset,
            vertical_offset,
            self._logical_width,
            self._logical_height,
            x,
            y,
            position_info["position"],
        )

        return self.clamp_to_work_area(QPoint(x, y))

    def _frame_width(self) -> int:
        return max(self.frameGeometry().width(), self.width())

    def _frame_height(self) -> int:
        return max(self.frameGeometry().height(), self.height())

    def set_keep_visible_enabled(self, enabled: bool) -> None:
        self._keep_visible_enabled = enabled

    def update_quote(self, quote: StockQuote | None) -> None:
        if quote is None:
            self.label.setText("No data")
            self._sync_size_to_content()
            return

        price_text = f"{quote.price:.2f}"
        if quote.change_percent > 0:
            change_color = "#ff4d4f"
            change_text = f"+{quote.change_percent:.2f}%"
        elif quote.change_percent < 0:
            change_color = "#2fbf71"
            change_text = f"{quote.change_percent:.2f}%"
        else:
            change_color = "#f5f5f5"
            change_text = "0.00%"

        self.label.setText(
            (
                f"<span style='color:#f5f5f5;'>{quote.name} {price_text} </span>"
                f"<span style='color:{change_color};'>({change_text})</span>"
            )
        )
        self._sync_size_to_content()

    def show_error(self, message: str) -> None:
        self.label.setText(f"Error: {message}")
        self._sync_size_to_content()

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        if self._keep_visible_enabled:
            self.keep_visible_requested.emit()

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        if (
            self._keep_visible_enabled
            and event.type() == QEvent.Type.WindowStateChange
            and self.windowState() & Qt.WindowState.WindowMinimized
        ):
            self.keep_visible_requested.emit()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and self._drag_offset is not None
        ):
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            new_pos = self.clamp_to_work_area(new_pos)
            self.move(new_pos)
            self.moved.emit(new_pos.x(), new_pos.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)
