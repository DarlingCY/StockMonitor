from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QIcon,
    QPainter,
    QPainterPath,
    QPixmap,
)

# Dark rounded tile + rising bars (A-share colors).
BG = "#1a1f24"
GREEN = "#2fbf71"
RED = "#ff4d4f"


def icon_corner_radius(size: int) -> float:
    """Corner radius scaled with icon size (~3.5px at 16px)."""
    return max(2.0, size * 22 / 100)


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
    """Rasterize the app/tray glyph with a rounded dark tile."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)

    radius = icon_corner_radius(size)
    # Half-pixel inset keeps the AA edge dark instead of clipping harshly.
    tile = QRectF(0.5, 0.5, size - 1.0, size - 1.0)
    path = QPainterPath()
    path.addRoundedRect(tile, radius, radius)

    painter.setBrush(QColor(BG))
    painter.drawPath(path)

    painter.setClipPath(path)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
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
