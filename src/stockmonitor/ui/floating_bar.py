from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QMouseEvent
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget

from stockmonitor.models.quote import StockQuote


class FloatingBar(QWidget):
    moved = Signal(int, int)

    def __init__(self, topmost: bool = True, background_color: str = "transparent"):
        super().__init__()
        self.setObjectName("FloatingBar")
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        if topmost:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
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
        self.resize(520, 44)

    def clamp_to_work_area(self, pos: QPoint) -> QPoint:
        screen = QGuiApplication.screenAt(pos)
        if screen is None:
            screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return pos

        area = screen.availableGeometry()
        x = max(area.left(), min(pos.x(), area.right() - self.width()))
        y = max(area.top(), min(pos.y(), area.bottom() - self.height()))
        return QPoint(x, y)

    def clamp_offset_to_screen(self, offset: QPoint) -> QPoint:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return offset

        area = screen.availableGeometry()
        max_x = max(0, area.width() - self.width())
        max_y = max(0, area.height() - self.height())
        x = max(0, min(offset.x(), max_x))
        y = max(0, min(offset.y(), max_y))
        return QPoint(x, y)

    def anchor_to_global(self, horizontal_align: str, vertical_align: str) -> QPoint:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return QPoint(0, 0)

        area = screen.availableGeometry()
        if horizontal_align == "right":
            x = area.right() - self.width()
        elif horizontal_align == "center":
            x = area.left() + (area.width() - self.width()) // 2
        else:
            x = area.left()

        if vertical_align == "bottom":
            y = area.bottom() - self.height()
        elif vertical_align == "center":
            y = area.top() + (area.height() - self.height()) // 2
        else:
            y = area.top()

        return self.clamp_to_work_area(QPoint(x, y))

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
