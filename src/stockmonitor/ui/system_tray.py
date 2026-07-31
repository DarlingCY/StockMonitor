from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QWidget,
    QWidgetAction,
)


class SystemTray:
    def __init__(
        self,
        on_add_symbol,
        on_remove_symbol,
        get_symbol_entries,
        on_set_horizontal_offset,
        on_set_vertical_offset,
        get_offsets,
        on_toggle_autostart,
        get_autostart,
        on_set_visibility_mode,
        get_visibility_mode,
        on_check_update,
        on_exit,
    ):
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self._create_icon())
        self.tray.setToolTip("StockMonitor")
        self._on_remove_symbol = on_remove_symbol
        self._get_symbol_entries = get_symbol_entries
        self._get_offsets = get_offsets
        self._get_autostart = get_autostart
        self._get_visibility_mode = get_visibility_mode
        self._on_set_horizontal_offset = on_set_horizontal_offset
        self._on_set_vertical_offset = on_set_vertical_offset

        self.menu = QMenu()
        self.add_symbol_menu = QMenu("增加股票")
        self.add_symbol_widget_action = QWidgetAction(self.add_symbol_menu)
        self.remove_symbol_menu = QMenu("删除股票")
        self.remove_symbol_menu.aboutToShow.connect(self._rebuild_remove_symbol_menu)
        self.position_menu = QMenu("位置配置")
        self.position_menu.aboutToShow.connect(self._refresh_position_menu)
        self.visibility_menu = QMenu("显示模式")

        self.horizontal_offset_action, self.horizontal_offset_input = (
            self._make_offset_row("横向偏移", self._submit_horizontal_offset)
        )
        self.vertical_offset_action, self.vertical_offset_input = (
            self._make_offset_row("纵向偏移", self._submit_vertical_offset)
        )
        self.autostart_action = QAction("开机自启")
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(bool(self._get_autostart()))
        self.autostart_action.triggered.connect(on_toggle_autostart)
        self.visibility_action_group = QActionGroup(self.visibility_menu)
        self.visibility_action_group.setExclusive(True)
        self.visibility_always_action = QAction("一直显示")
        self.visibility_always_action.setCheckable(True)
        self.visibility_always_action.triggered.connect(
            lambda checked: checked and on_set_visibility_mode("always")
        )
        self.visibility_trading_time_action = QAction("交易时间显示")
        self.visibility_trading_time_action.setCheckable(True)
        self.visibility_trading_time_action.triggered.connect(
            lambda checked: checked and on_set_visibility_mode("trading_time")
        )
        self.visibility_action_group.addAction(self.visibility_always_action)
        self.visibility_action_group.addAction(self.visibility_trading_time_action)
        self.visibility_menu.addAction(self.visibility_always_action)
        self.visibility_menu.addAction(self.visibility_trading_time_action)
        self.check_update_action = QAction("检查更新")
        self.check_update_action.triggered.connect(lambda: on_check_update())
        self.exit_action = QAction("退出")
        self.exit_action.triggered.connect(on_exit)

        self.add_symbol_widget = QWidget(self.add_symbol_menu)
        self.add_symbol_layout = QHBoxLayout(self.add_symbol_widget)
        self.add_symbol_layout.setContentsMargins(8, 4, 8, 4)
        self.add_symbol_layout.setSpacing(6)
        self.symbol_input = QLineEdit(self.add_symbol_widget)
        self.symbol_input.setPlaceholderText("输入6位A股代码")
        self.symbol_input.setMaxLength(6)
        self.symbol_input.setClearButtonEnabled(True)
        self.symbol_input.setFixedWidth(88)
        self.add_symbol_button = QPushButton("添加", self.add_symbol_widget)
        self.add_symbol_button.setFixedWidth(48)
        self.add_symbol_button.clicked.connect(
            lambda: self._submit_add_symbol(on_add_symbol)
        )
        self.symbol_input.returnPressed.connect(
            lambda: self._submit_add_symbol(on_add_symbol)
        )
        self.add_symbol_layout.addWidget(self.symbol_input)
        self.add_symbol_layout.addWidget(self.add_symbol_button)
        self.add_symbol_widget_action.setDefaultWidget(self.add_symbol_widget)
        self.add_symbol_menu.addAction(self.add_symbol_widget_action)

        self.position_menu.addAction(self.horizontal_offset_action)
        self.position_menu.addAction(self.vertical_offset_action)

        self.menu.addMenu(self.add_symbol_menu)
        self.menu.addMenu(self.remove_symbol_menu)
        self.menu.addMenu(self.position_menu)
        self.menu.addMenu(self.visibility_menu)
        self.menu.addAction(self.autostart_action)
        self.menu.addSeparator()
        self.menu.addAction(self.check_update_action)
        self.menu.addAction(self.exit_action)
        self.tray.setContextMenu(self.menu)
        self.set_visibility_mode(self._get_visibility_mode())

    def _make_offset_row(
        self, placeholder: str, on_submit
    ) -> tuple[QWidgetAction, QLineEdit]:
        action = QWidgetAction(self.position_menu)
        widget = QWidget(self.position_menu)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        edit = QLineEdit(widget)
        edit.setPlaceholderText(placeholder)
        edit.setFixedWidth(70)
        button = QPushButton("设置", widget)
        button.setFixedWidth(48)
        button.clicked.connect(on_submit)
        edit.returnPressed.connect(on_submit)
        layout.addWidget(edit)
        layout.addWidget(button)
        action.setDefaultWidget(widget)
        return action, edit

    def _create_icon(self) -> QIcon:
        """Paint opaque tray glyphs — transparent AA edges show as a white halo."""
        icon = QIcon()
        for size in (16, 20, 24, 32):
            icon.addPixmap(self._paint_tray_pixmap(size))
        return icon

    @staticmethod
    def _paint_tray_pixmap(size: int) -> QPixmap:
        pixmap = QPixmap(size, size)
        painter = QPainter(pixmap)
        use_aa = size >= 24
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, use_aa)

        s = size / 16.0
        painter.scale(s, s)

        # Fully opaque tile: no alpha fringe on Windows taskbar.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#1a1f24"))
        if use_aa:
            painter.drawRoundedRect(0.5, 0.5, 15.0, 15.0, 3.0, 3.0)
        else:
            painter.drawRect(0, 0, 16, 16)

        green = QColor("#2fbf71")
        red = QColor("#ff4d4f")
        ink = QColor("#f0f0f0")

        painter.setBrush(green)
        painter.drawRect(2, 9, 3, 5)
        painter.drawRect(6, 10, 3, 4)
        painter.setBrush(red)
        painter.drawRect(10, 6, 3, 8)

        painter.setPen(
            QPen(
                ink,
                1.3 if use_aa else 1.0,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap if use_aa else Qt.PenCapStyle.SquareCap,
                Qt.PenJoinStyle.RoundJoin if use_aa else Qt.PenJoinStyle.MiterJoin,
            )
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        path.moveTo(1.5, 12)
        path.lineTo(4, 8)
        path.lineTo(7, 10)
        path.lineTo(11, 5)
        path.lineTo(13.5, 3)
        painter.drawPath(path)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(red)
        if use_aa:
            painter.drawEllipse(12.4, 1.6, 2.8, 2.8)
        else:
            painter.drawRect(13, 2, 2, 2)

        painter.end()
        return pixmap

    def show(self) -> None:
        self.tray.show()

    def hide(self) -> None:
        self.tray.hide()

    def show_message(self, title: str, message: str) -> None:
        self.tray.showMessage(title, message)

    def update_symbols(self, entries: list[tuple[str, str]]) -> None:
        """Rebuild the remove menu. Each entry is (symbol, display_name)."""
        self.remove_symbol_menu.clear()
        if not entries:
            action = QAction("无可删除股票")
            action.setEnabled(False)
            self.remove_symbol_menu.addAction(action)
            return

        for symbol, name in entries:
            row_widget = QWidget(self.remove_symbol_menu)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(8, 4, 8, 4)
            row_layout.setSpacing(6)

            name_label = QLabel(name or symbol, row_widget)
            name_label.setMinimumWidth(72)

            delete_button = QPushButton("删除", row_widget)
            delete_button.setFixedWidth(48)
            delete_button.clicked.connect(partial(self._on_remove_symbol, symbol))

            row_layout.addWidget(name_label, 1)
            row_layout.addWidget(delete_button)

            action = QWidgetAction(self.remove_symbol_menu)
            action.setDefaultWidget(row_widget)
            self.remove_symbol_menu.addAction(action)

    def _rebuild_remove_symbol_menu(self) -> None:
        self.update_symbols(self._get_symbol_entries())

    def _refresh_position_menu(self) -> None:
        horizontal_offset, vertical_offset = self._get_offsets()
        self.horizontal_offset_input.setText(str(horizontal_offset))
        self.vertical_offset_input.setText(str(vertical_offset))

    def set_autostart_checked(self, checked: bool) -> None:
        self.autostart_action.setChecked(checked)

    def set_visibility_mode(self, mode: str) -> None:
        if mode == "always":
            self.visibility_always_action.setChecked(True)
            return
        self.visibility_trading_time_action.setChecked(True)

    def _submit_horizontal_offset(self) -> None:
        text = self.horizontal_offset_input.text().strip()
        if not text:
            return
        try:
            offset = int(text)
            self._on_set_horizontal_offset(offset)
        except ValueError:
            pass

    def _submit_vertical_offset(self) -> None:
        text = self.vertical_offset_input.text().strip()
        if not text:
            return
        try:
            offset = int(text)
            self._on_set_vertical_offset(offset)
        except ValueError:
            pass

    def _submit_add_symbol(self, on_add_symbol) -> None:
        symbol = self.symbol_input.text().strip()
        if not symbol:
            return
        if on_add_symbol(symbol):
            self.symbol_input.clear()
            self.menu.hide()
