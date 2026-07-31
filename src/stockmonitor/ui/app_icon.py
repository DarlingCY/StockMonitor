from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPixmap

# Opaque bars on a solid dark tile — no alpha fringe on Windows chrome.
BG = "#1a1f24"
GREEN = "#2fbf71"
RED = "#ff4d4f"


def icon_bars(size: int) -> list[tuple[int, int, int, int, str]]:
    """Axis-aligned bar rects for a size×size icon: (x, y, w, h, color)."""

    def px(n: int) -> int:
        return (n * size) // 16

    gap = max(1, px(1))
    bar_w = max(2, px(3))
    base = px(14)
    specs = (
        (px(2), px(9), GREEN),
        (px(2) + bar_w + gap, px(7), GREEN),
        (px(2) + 2 * (bar_w + gap), px(4), RED),
    )
    return [
        (x, top, bar_w, max(1, base - top), color) for x, top, color in specs
    ]


def paint_icon_pixmap(size: int) -> QPixmap:
    """Rasterize the app/tray glyph at an exact pixel size (fully opaque)."""
    pixmap = QPixmap(size, size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.fillRect(0, 0, size, size, QColor(BG))
    for x, y, w, h, color in icon_bars(size):
        painter.fillRect(x, y, w, h, QColor(color))
    painter.end()
    return pixmap


def make_app_icon() -> QIcon:
    """Multi-resolution icon for tray / window, DPI-aware."""
    icon = QIcon()
    screen = QGuiApplication.primaryScreen()
    dpr = float(screen.devicePixelRatio()) if screen is not None else 1.0
    for logical in (16, 20, 24, 32, 48, 64, 128, 256):
        physical = max(logical, int(round(logical * dpr)))
        pixmap = paint_icon_pixmap(physical)
        pixmap.setDevicePixelRatio(physical / logical)
        icon.addPixmap(pixmap)
    return icon
