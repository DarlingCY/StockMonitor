from __future__ import annotations

import sys

import httpx
from loguru import logger
from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtWidgets import QApplication

from stockmonitor.config.settings import Settings
from stockmonitor.services.state_store import StateStore
from stockmonitor.services.stock_api import StockAPI
from stockmonitor.services.window_behavior import (
    ForegroundWatchdog,
    apply_windows_extended_styles,
    reassert_topmost,
)
from stockmonitor.ui.floating_bar import FloatingBar
from stockmonitor.ui.system_tray import SystemTray
from stockmonitor.models.quote import StockQuote


class StockMonitorApp:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)
        self.state_store = StateStore(settings.state_file)
        self.api = StockAPI()
        self.symbols = self.state_store.load_symbols() or settings.symbols_list
        saved_offsets = self.state_store.load_offsets()
        if saved_offsets:
            self.horizontal_offset, self.vertical_offset = saved_offsets
        else:
            self.horizontal_offset = settings.horizontal_offset
            self.vertical_offset = settings.vertical_offset
        self._quotes: list[StockQuote] = []
        self._display_index = 0
        self._topmost_burst_remaining = 0

        self.window = FloatingBar(
            topmost=settings.auto_topmost,
            background_color=settings.background_color,
        )
        self.window.moved.connect(self.state_store.save_position)
        self.window.keep_visible_requested.connect(self._restore_window_visibility)
        self.window.show()

        self.qt_app.processEvents()
        hwnd = int(self.window.winId())
        self._window_hwnd = hwnd
        apply_windows_extended_styles(hwnd, topmost=settings.auto_topmost)
        self.qt_app.applicationStateChanged.connect(self._handle_application_state_change)
        self._topmost_burst_timer = QTimer()
        self._topmost_burst_timer.setInterval(250)
        self._topmost_burst_timer.timeout.connect(self._run_topmost_burst)
        self._foreground_watchdog = ForegroundWatchdog()
        self._foreground_watchdog.foreground_changed.connect(
            self._handle_foreground_changed
        )
        self._foreground_watchdog.start()

        pos = self.state_store.load_position()
        position_mode = self.state_store.load_position_mode()
        if pos and position_mode != "anchor":
            self._apply_window_position(self.window.clamp_to_work_area(QPoint(*pos)))
        else:
            self._apply_window_position(
                self.window.anchor_to_global(
                    horizontal_offset=self.horizontal_offset,
                    vertical_offset=self.vertical_offset,
                )
            )

        self.tray = SystemTray(
            on_add_symbol=self.add_symbol,
            on_remove_symbol=self.remove_symbol,
            get_symbols=self.get_symbols,
            on_set_horizontal_offset=self.set_horizontal_offset,
            on_set_vertical_offset=self.set_vertical_offset,
            get_offsets=self.get_offsets,
            on_exit=self.exit_app,
        )
        self.tray.update_symbols(self.symbols)
        self.tray.show()

        self.refresh_timer = QTimer()
        self.refresh_timer.setInterval(max(1, settings.refresh_interval_seconds) * 1000)
        self.refresh_timer.timeout.connect(self.refresh_quotes)
        self.refresh_timer.start()

        self.rotate_timer = QTimer()
        self.rotate_timer.setInterval(3000)
        self.rotate_timer.timeout.connect(self.rotate_quote)
        self.rotate_timer.start()

        self.refresh_quotes()

    def refresh_quotes(self) -> None:
        try:
            quotes = self.api.fetch_quotes(self.symbols)
            if quotes:
                self._quotes = quotes
                self._display_index = 0
                self.window.update_quote(self._quotes[0])
            else:
                self._quotes = []
                self.window.show_error("No quote data")
        except httpx.HTTPError as exc:
            logger.error("Quote request failed: {}", exc)
            self._quotes = []
            self.window.show_error("Request failed")
        except Exception as exc:
            logger.exception("Unexpected refresh error: {}", exc)
            self._quotes = []
            self.window.show_error("Unexpected error")

    def add_symbol(self, symbol: str) -> bool:
        normalized = self._normalize_symbol(symbol)
        if normalized is None:
            self.tray.show_message("输入无效", "请输入有效的 6 位 A 股代码。")
            return False

        if normalized in self.symbols:
            self.tray.show_message("已存在", f"{normalized} 已在监控列表中。")
            return False

        try:
            if not self.api.validate_symbol(normalized):
                self.tray.show_message("代码不存在", f"未找到股票代码 {normalized}")
                return False
        except httpx.HTTPError as exc:
            logger.error("Symbol validation request failed: {}", exc)
            self.tray.show_message("校验失败", "暂时无法校验股票代码，请稍后重试。")
            return False
        except Exception as exc:
            logger.exception("Unexpected symbol validation error: {}", exc)
            self.tray.show_message("校验失败", "校验股票代码时发生异常。")
            return False

        self.symbols.append(normalized)
        self.state_store.save_symbols(self.symbols)
        self.tray.update_symbols(self.symbols)
        self.refresh_quotes()
        self.tray.show_message("添加成功", f"已添加股票代码 {normalized}")
        return True

    def remove_symbol(self, symbol: str) -> None:
        if symbol not in self.symbols:
            return
        self.symbols = [item for item in self.symbols if item != symbol]
        self.state_store.save_symbols(self.symbols)
        self.tray.update_symbols(self.symbols)
        self._quotes = [quote for quote in self._quotes if quote.symbol != symbol]
        self._display_index = 0
        if self._quotes:
            self.window.update_quote(self._quotes[0])
        elif self.symbols:
            self.refresh_quotes()
        else:
            self.window.show_error("No symbols configured")

    def get_symbols(self) -> list[str]:
        return list(self.symbols)

    def get_offsets(self) -> tuple[int, int]:
        return self.horizontal_offset, self.vertical_offset

    def set_horizontal_offset(self, offset: int) -> None:
        self.horizontal_offset = offset
        self._apply_anchor_position()

    def set_vertical_offset(self, offset: int) -> None:
        self.vertical_offset = offset
        self._apply_anchor_position()

    def _apply_anchor_position(self) -> None:
        self.state_store.save_offsets(self.horizontal_offset, self.vertical_offset)
        self._apply_window_position(
            self.window.anchor_to_global(
                horizontal_offset=self.horizontal_offset,
                vertical_offset=self.vertical_offset,
            )
        )

    def _apply_window_position(self, pos: QPoint) -> None:
        logger.info(
            "_apply_window_position PRE-move: frame={}, move_to={}",
            self.window.frameGeometry().getRect(),
            (pos.x(), pos.y()),
        )
        self.window.move(pos)
        logger.info(
            "_apply_window_position POST-move: frame={}",
            self.window.frameGeometry().getRect(),
        )

    def _handle_application_state_change(
        self, state: Qt.ApplicationState
    ) -> None:
        if state == Qt.ApplicationState.ApplicationActive:
            return
        self._restore_window_visibility()

    def _handle_foreground_changed(self) -> None:
        self._start_topmost_burst()

    def _start_topmost_burst(self) -> None:
        if not self.settings.auto_topmost:
            return
        if not self.window.isVisible():
            return
        if self._topmost_burst_timer.isActive():
            return
        self._topmost_burst_remaining = 6
        reassert_topmost(self._window_hwnd, topmost=True)
        self._topmost_burst_timer.start()

    def _run_topmost_burst(self) -> None:
        if self._topmost_burst_remaining <= 0:
            self._topmost_burst_timer.stop()
            return
        self._topmost_burst_remaining -= 1
        reassert_topmost(self._window_hwnd, topmost=self.settings.auto_topmost)

    def _restore_window_visibility(self) -> None:
        if self.window.isMinimized():
            self.window.showNormal()
        else:
            self.window.show()
        reassert_topmost(self._window_hwnd, topmost=self.settings.auto_topmost)
        self._start_topmost_burst()

    @staticmethod
    def _normalize_symbol(value: str) -> str | None:
        normalized = value.strip().upper()
        if (
            len(normalized) == 6
            and normalized.isdigit()
            and normalized[0] in {"0", "2", "3", "5", "6", "9"}
        ):
            return normalized
        return None

    def rotate_quote(self) -> None:
        if not self._quotes:
            return
        self._display_index = (self._display_index + 1) % len(self._quotes)
        self.window.update_quote(self._quotes[self._display_index])

    def exit_app(self) -> None:
        pos = self.window.pos()
        self.state_store.save_position(pos.x(), pos.y())
        self.state_store.save_symbols(self.symbols)
        self.window.set_keep_visible_enabled(False)
        self._topmost_burst_timer.stop()
        self._foreground_watchdog.stop()
        self.tray.hide()
        self.qt_app.quit()

    def run(self) -> int:
        logger.info("StockMonitor started")
        return self.qt_app.exec()
