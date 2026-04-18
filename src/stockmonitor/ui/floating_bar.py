from __future__ import annotations

from loguru import logger
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QMouseEvent
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget

from stockmonitor.models.quote import StockQuote
from stockmonitor.services.taskbar_utils import TaskbarUtils


class FloatingBar(QWidget):
    moved = Signal(int, int)

    def __init__(self, topmost: bool = True, background_color: str = "transparent"):
        super().__init__()
        self.setObjectName("FloatingBar")
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.NoDropShadowWindowHint
        )
        if topmost:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setContentsMargins(0, 0, 0, 0)
        self._logical_width = 520
        self._logical_height = 44
        self.setStyleSheet(
            f"""
            #FloatingBar {{
                background-color: {background_color};
                color: #f5f5f5;
                border: 1px solid rgba(255, 255, 255, 0.35);
                border-radius: 8px;
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
        self.label.setMargin(10)
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.resize(self._logical_width, self._logical_height)

    def clamp_to_work_area(self, pos: QPoint) -> QPoint:
        # Use the logical dimensions to avoid frameGeometry timing issues
        win_width = self._logical_width
        win_height = self._logical_height

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

        # Calculate bounds
        min_x = area.left()
        min_y = area.top()
        max_x = area.left() + max(0, area.width() - win_width)
        max_y = area.top() + max(0, area.height() - win_height)

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
        frame_width = self._frame_width()
        frame_height = self._frame_height()
        max_x = max(0, area.width() - frame_width)
        max_y = max(0, area.height() - frame_height)
        x = max(0, min(offset.x(), max_x))
        y = max(0, min(offset.y(), max_y))
        return QPoint(x, y)

    def anchor_to_global(self, horizontal_align: str, vertical_align: str) -> QPoint:
        """Calculate optimal position based on taskbar position and alignment.

        Uses Win32 API to detect taskbar position and calculates the optimal
        window position based on the specified horizontal and vertical alignment.
        Uses the pre-set widget dimensions (_logical_width, _logical_height)
        to avoid frameGeometry timing issues.
        """
        position_info = TaskbarUtils.calculate_optimal_position(
            window_width=self._logical_width,
            window_height=self._logical_height,
            margin=5,
            horizontal_align=horizontal_align,
            vertical_align=vertical_align,
        )

        x = position_info["x"]
        y = position_info["y"]

        logger.info(
            "Anchor position computed: align=({}, {}), logical=({},{}), target=({}, {}), position={}",
            horizontal_align,
            vertical_align,
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

    def update_quote(self, quote: StockQuote | None) -> None:
        if quote is None:
            self.label.setText("No data")
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

    def show_error(self, message: str) -> None:
        self.label.setText(f"Error: {message}")

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
