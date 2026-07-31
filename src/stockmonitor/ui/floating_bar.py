from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QMouseEvent
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget

from stockmonitor.models.quote import StockQuote
from stockmonitor.services.taskbar_utils import TaskbarUtils


class FloatingBar(QWidget):
    moved = Signal(int, int)
    keep_visible_requested = Signal()

    def __init__(self, topmost: bool = True):
        super().__init__()
        self.setObjectName("FloatingBar")
        self._keep_visible_enabled = True
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
            """
            #FloatingBar {
                color: #f5f5f5;
                font-size: 13px;
            }
            QLabel {
                color: #f5f5f5;
                background: transparent;
                border: none;
            }
            """
        )
        self._drag_offset: QPoint | None = None
        self._last_label_text: str | None = None

        self.label = QLabel("Loading...")
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setMargin(0)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self._sync_size_to_content()

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

        current_screen = self.screen()
        if current_screen is None:
            current_screen = QGuiApplication.primaryScreen()
        if current_screen is None:
            return pos

        screen = QGuiApplication.screenAt(pos)
        if screen is None:
            screen = current_screen

        area = screen.availableGeometry()
        screen_geometry = screen.geometry()

        # Horizontal respects available work area (left/right taskbar).
        # Vertical uses full screen geometry so the bar can sit in taskbar space.
        min_x = area.left()
        max_x = area.left() + max(0, area.width() - win_width)
        min_y = screen_geometry.top()
        max_y = screen_geometry.top() + max(0, screen_geometry.height() - win_height)

        return QPoint(
            max(min_x, min(pos.x(), max_x)),
            max(min_y, min(pos.y(), max_y)),
        )

    def anchor_to_global(
        self,
        horizontal_offset: int = 0,
        vertical_offset: int = 0,
    ) -> QPoint:
        position_info = TaskbarUtils.calculate_optimal_position(
            window_width=self._logical_width,
            window_height=self._logical_height,
            margin=0,
            horizontal_offset=horizontal_offset,
            vertical_offset=vertical_offset,
        )
        return self.clamp_to_work_area(
            QPoint(position_info["x"], position_info["y"])
        )

    def set_keep_visible_enabled(self, enabled: bool) -> None:
        self._keep_visible_enabled = enabled

    def _set_label_text(self, text: str) -> None:
        if text == self._last_label_text:
            return
        self._last_label_text = text
        self.label.setText(text)
        self._sync_size_to_content()

    def update_quote(self, quote: StockQuote | None) -> None:
        if quote is None:
            self._set_label_text("No data")
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

        html = (
            f"<span style='color:#f5f5f5;'>{quote.name} {price_text} </span>"
            f"<span style='color:{change_color};'>({change_text})</span>"
        )
        self._set_label_text(html)

    def show_error(self, message: str) -> None:
        self._set_label_text(f"Error: {message}")

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
