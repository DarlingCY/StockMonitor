from __future__ import annotations

import sys

import httpx
from loguru import logger
from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QApplication

from stockmonitor.config.settings import Settings
from stockmonitor.services.state_store import StateStore
from stockmonitor.services.stock_api import StockAPI
from stockmonitor.services.window_behavior import apply_windows_extended_styles
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
        saved_alignment = self.state_store.load_alignment()
        if saved_alignment:
            self.horizontal_align, self.vertical_align = saved_alignment
        else:
            self.horizontal_align = settings.normalized_horizontal_align
            self.vertical_align = settings.normalized_vertical_align
        self._quotes: list[StockQuote] = []
        self._display_index = 0

        self.window = FloatingBar(
            topmost=settings.auto_topmost,
            background_color=settings.background_color,
        )
        pos = self.state_store.load_position()
        position_mode = self.state_store.load_position_mode()
        if pos and position_mode != "anchor":
            self.window.move(self.window.clamp_to_work_area(QPoint(*pos)))
        else:
            self.window.move(
                self.window.anchor_to_global(
                    self.horizontal_align,
                    self.vertical_align,
                )
            )

        self.window.moved.connect(self.state_store.save_position)
        self.window.show()

        self.qt_app.processEvents()
        hwnd = int(self.window.winId())
        apply_windows_extended_styles(hwnd, topmost=settings.auto_topmost)

        self.tray = SystemTray(
            on_add_symbol=self.add_symbol,
            on_remove_symbol=self.remove_symbol,
            get_symbols=self.get_symbols,
            on_set_horizontal_align=self.set_horizontal_align,
            on_set_vertical_align=self.set_vertical_align,
            get_alignment=self.get_alignment,
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

    def get_alignment(self) -> tuple[str, str]:
        return self.horizontal_align, self.vertical_align

    def set_horizontal_align(self, alignment: str) -> None:
        normalized = alignment.strip().lower()
        if normalized not in {"left", "center", "right"}:
            return
        self.horizontal_align = normalized
        self._apply_anchor_position()

    def set_vertical_align(self, alignment: str) -> None:
        normalized = alignment.strip().lower()
        if normalized not in {"top", "center", "bottom"}:
            return
        self.vertical_align = normalized
        self._apply_anchor_position()

    def _apply_anchor_position(self) -> None:
        self.state_store.save_alignment(self.horizontal_align, self.vertical_align)
        self.window.move(
            self.window.anchor_to_global(self.horizontal_align, self.vertical_align)
        )

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
        self.tray.hide()
        self.qt_app.quit()

    def run(self) -> int:
        logger.info("StockMonitor started")
        return self.qt_app.exec()
