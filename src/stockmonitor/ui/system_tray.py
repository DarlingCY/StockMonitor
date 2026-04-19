from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
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
        get_symbols,
        on_set_horizontal_offset,
        on_set_vertical_offset,
        get_offsets,
        on_toggle_autostart,
        get_autostart,
        on_exit,
    ):
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self._create_icon())
        self.tray.setToolTip("StockMonitor")
        self._on_remove_symbol = on_remove_symbol
        self._get_symbols = get_symbols
        self._get_offsets = get_offsets
        self._get_autostart = get_autostart
        self._on_set_horizontal_offset = on_set_horizontal_offset
        self._on_set_vertical_offset = on_set_vertical_offset

        self.menu = QMenu()
        self.add_symbol_menu = QMenu("增加股票代码")
        self.add_symbol_widget_action = QWidgetAction(self.add_symbol_menu)
        self.remove_symbol_menu = QMenu("删除股票代码")
        self.remove_symbol_menu.aboutToShow.connect(self._rebuild_remove_symbol_menu)
        self.position_menu = QMenu("位置配置")
        self.position_menu.aboutToShow.connect(self._refresh_position_menu)

        # Horizontal offset input
        self.horizontal_offset_action = QWidgetAction(self.position_menu)
        self.horizontal_offset_widget = QWidget(self.position_menu)
        self.horizontal_offset_layout = QHBoxLayout(self.horizontal_offset_widget)
        self.horizontal_offset_layout.setContentsMargins(8, 4, 8, 4)
        self.horizontal_offset_layout.setSpacing(6)
        self.horizontal_offset_input = QLineEdit(self.horizontal_offset_widget)
        self.horizontal_offset_input.setPlaceholderText("横向偏移")
        self.horizontal_offset_input.setFixedWidth(70)
        self.horizontal_offset_button = QPushButton(
            "设置", self.horizontal_offset_widget
        )
        self.horizontal_offset_button.setFixedWidth(48)
        self.horizontal_offset_button.clicked.connect(self._submit_horizontal_offset)
        self.horizontal_offset_input.returnPressed.connect(
            self._submit_horizontal_offset
        )
        self.horizontal_offset_layout.addWidget(self.horizontal_offset_input)
        self.horizontal_offset_layout.addWidget(self.horizontal_offset_button)
        self.horizontal_offset_action.setDefaultWidget(self.horizontal_offset_widget)

        # Vertical offset input
        self.vertical_offset_action = QWidgetAction(self.position_menu)
        self.vertical_offset_widget = QWidget(self.position_menu)
        self.vertical_offset_layout = QHBoxLayout(self.vertical_offset_widget)
        self.vertical_offset_layout.setContentsMargins(8, 4, 8, 4)
        self.vertical_offset_layout.setSpacing(6)
        self.vertical_offset_input = QLineEdit(self.vertical_offset_widget)
        self.vertical_offset_input.setPlaceholderText("纵向偏移")
        self.vertical_offset_input.setFixedWidth(70)
        self.vertical_offset_button = QPushButton("设置", self.vertical_offset_widget)
        self.vertical_offset_button.setFixedWidth(48)
        self.vertical_offset_button.clicked.connect(self._submit_vertical_offset)
        self.vertical_offset_input.returnPressed.connect(self._submit_vertical_offset)
        self.vertical_offset_layout.addWidget(self.vertical_offset_input)
        self.vertical_offset_layout.addWidget(self.vertical_offset_button)
        self.vertical_offset_action.setDefaultWidget(self.vertical_offset_widget)
        self.autostart_action = QAction("开机自启")
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(bool(self._get_autostart()))
        self.autostart_action.triggered.connect(on_toggle_autostart)
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
        self.menu.addAction(self.autostart_action)
        self.menu.addSeparator()
        self.menu.addAction(self.exit_action)
        self.tray.setContextMenu(self.menu)

    def _create_icon(self) -> QIcon:
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2ECC71"))
        painter.drawEllipse(1, 1, 14, 14)
        painter.end()
        return QIcon(pixmap)

    def show(self) -> None:
        self.tray.show()

    def hide(self) -> None:
        self.tray.hide()

    def show_message(self, title: str, message: str) -> None:
        self.tray.showMessage(title, message)

    def update_symbols(self, symbols: list[str]) -> None:
        self.remove_symbol_menu.clear()
        if not symbols:
            action = QAction("无可删除股票")
            action.setEnabled(False)
            self.remove_symbol_menu.addAction(action)
            return

        for symbol in symbols:
            row_widget = QWidget(self.remove_symbol_menu)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(8, 4, 8, 4)
            row_layout.setSpacing(6)

            symbol_input = QLineEdit(row_widget)
            symbol_input.setText(symbol)
            symbol_input.setReadOnly(True)
            symbol_input.setEnabled(False)
            symbol_input.setFixedWidth(88)

            delete_button = QPushButton("删除", row_widget)
            delete_button.setFixedWidth(48)
            delete_button.clicked.connect(partial(self._on_remove_symbol, symbol))

            row_layout.addWidget(symbol_input)
            row_layout.addWidget(delete_button)

            action = QWidgetAction(self.remove_symbol_menu)
            action.setDefaultWidget(row_widget)
            self.remove_symbol_menu.addAction(action)

    def _rebuild_remove_symbol_menu(self) -> None:
        self.update_symbols(self._get_symbols())

    def _refresh_position_menu(self) -> None:
        horizontal_offset, vertical_offset = self._get_offsets()
        self.horizontal_offset_input.setText(str(horizontal_offset))
        self.vertical_offset_input.setText(str(vertical_offset))

    def set_autostart_checked(self, checked: bool) -> None:
        self.autostart_action.setChecked(checked)

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
