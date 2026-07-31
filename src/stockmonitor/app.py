from __future__ import annotations

import sys

import httpx
from loguru import logger
from PySide6.QtCore import QPoint, QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import QApplication

from stockmonitor.config.settings import Settings
from stockmonitor.services import autostart
from stockmonitor.services.state_store import StateStore
from stockmonitor.services.stock_api import StockAPI
from stockmonitor.services.trading_time_gate import is_visible as is_market_visible
from stockmonitor.services.window_behavior import (
    ForegroundWatchdog,
    apply_windows_extended_styles,
    reassert_topmost,
)
from stockmonitor.ui.floating_bar import FloatingBar
from stockmonitor.ui.system_tray import SystemTray
from stockmonitor.ui.update_controller import UpdateController
from stockmonitor.models.quote import StockQuote
from datetime import datetime


class _QuoteFetchWorker(QThread):
    """Fetches quotes off the GUI thread to avoid blocking the UI on network I/O.

    Owns its own StockAPI (and thus its own httpx.Client) so the connection is
    reused across fetches without sharing a client across threads.
    """

    # (quotes | None, status) where status in {"ok", "empty", "http_error", "error"}
    result = Signal(object, str)

    def __init__(self, symbols: list[str], parent=None) -> None:
        super().__init__(parent)
        self._symbols = symbols
        self._api = StockAPI()

    def run(self) -> None:
        try:
            quotes = self._api.fetch_quotes(self._symbols)
            if quotes:
                self.result.emit(quotes, "ok")
            else:
                self.result.emit(None, "empty")
        except httpx.HTTPError as exc:
            logger.error("Quote request failed: {}", exc)
            self.result.emit(None, "http_error")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected refresh error: {}", exc)
            self.result.emit(None, "error")
        finally:
            self._api.close()



class StockMonitorApp:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)
        self.state_store = StateStore(settings.state_file)
        self.api = StockAPI()
        self.symbols = self.state_store.load_symbols() or settings.symbols_list
        # Repair stale Run entries (e.g. console Scripts\stockmonitor) so boot
        # does not flash a CMD window.
        autostart.sync_command()
        self.autostart_enabled = autostart.is_enabled()
        self.visibility_mode = self.state_store.load_visibility_mode() or "trading_time"
        saved_offsets = self.state_store.load_offsets()
        if saved_offsets:
            self.horizontal_offset, self.vertical_offset = saved_offsets
        else:
            self.horizontal_offset = settings.horizontal_offset
            self.vertical_offset = settings.vertical_offset
        self._quotes: list[StockQuote] = []
        self._display_index = 0
        self._topmost_burst_remaining = 0
        self._quote_worker: _QuoteFetchWorker | None = None

        # Debounce position persistence so dragging doesn't write JSON on every
        # mouse-move event. We store the latest position and flush after idle.
        self._pending_position: tuple[int, int] | None = None
        self._save_position_timer = QTimer()
        self._save_position_timer.setSingleShot(True)
        self._save_position_timer.setInterval(400)
        self._save_position_timer.timeout.connect(self._flush_pending_position)

        self.window = FloatingBar(topmost=settings.auto_topmost)
        self.window.moved.connect(self._on_window_moved)
        self.window.keep_visible_requested.connect(self._restore_window_visibility)
        if self._should_show_window():
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
            get_symbol_entries=self.get_symbol_entries,
            on_set_horizontal_offset=self.set_horizontal_offset,
            on_set_vertical_offset=self.set_vertical_offset,
            get_offsets=self.get_offsets,
            on_toggle_autostart=self.toggle_autostart,
            get_autostart=self.get_autostart,
            on_set_visibility_mode=self.set_visibility_mode,
            get_visibility_mode=self.get_visibility_mode,
            on_check_update=self.check_for_update,
            on_exit=self.exit_app,
        )
        self.tray.show()

        self.update_controller = UpdateController(notify=self.tray.show_message)

        self.refresh_timer = QTimer()
        self.refresh_timer.setInterval(max(1, settings.refresh_interval_seconds) * 1000)
        self.refresh_timer.timeout.connect(self.refresh_quotes)
        self.refresh_timer.start()

        self.rotate_timer = QTimer()
        self.rotate_timer.setInterval(3000)
        self.rotate_timer.timeout.connect(self.rotate_quote)
        self.rotate_timer.start()

        # Periodic (daily) update check.
        self.update_check_timer = QTimer()
        self.update_check_timer.setInterval(24 * 60 * 60 * 1000)
        self.update_check_timer.timeout.connect(
            lambda: self.update_controller.check(silent=True)
        )
        self.update_check_timer.start()
        # Initial check shortly after startup so the UI is up first.
        QTimer.singleShot(8000, lambda: self.update_controller.check(silent=True))

        self.refresh_quotes()

    def refresh_quotes(self) -> None:
        if not self._should_show_window():
            self._quotes = []
            self.window.hide()
            return

        if not self.window.isVisible():
            self.window.show()
            reassert_topmost(self._window_hwnd, topmost=self.settings.auto_topmost)

        if not self.symbols:
            self._quotes = []
            self.window.show_error("No symbols configured")
            return

        # Skip if a fetch is already in flight to avoid piling up threads.
        if self._quote_worker is not None and self._quote_worker.isRunning():
            return

        worker = _QuoteFetchWorker(list(self.symbols))
        worker.result.connect(
            self._on_quotes_fetched, Qt.ConnectionType.QueuedConnection
        )
        worker.finished.connect(lambda w=worker: self._clear_quote_worker(w))
        worker.finished.connect(worker.deleteLater)
        self._quote_worker = worker
        worker.start()

    def _clear_quote_worker(self, worker) -> None:
        # Only clear if the finishing worker is still the current one, so a
        # newer worker started in the meantime is not accidentally dropped.
        if self._quote_worker is worker:
            self._quote_worker = None

    def _on_window_moved(self, x: int, y: int) -> None:
        # Keep only the latest position; persist once movement settles.
        self._pending_position = (x, y)
        self._save_position_timer.start()

    def _flush_pending_position(self) -> None:
        if self._pending_position is None:
            return
        x, y = self._pending_position
        self._pending_position = None
        self.state_store.save_position(x, y)

    def _on_quotes_fetched(self, quotes, status: str) -> None:
        if status != "ok" or not quotes:
            self._quotes = []
            if status == "empty":
                self.window.show_error("No quote data")
            elif status == "http_error":
                self.window.show_error("Request failed")
            elif status == "error":
                self.window.show_error("Unexpected error")
            return

        # Preserve the rotation position across refreshes so the periodic data
        # refresh does not reset/skip the carousel.
        current_symbol = None
        if self._quotes and 0 <= self._display_index < len(self._quotes):
            current_symbol = self._quotes[self._display_index].symbol

        had_quotes = bool(self._quotes)
        self._quotes = quotes

        new_index = 0
        if current_symbol is not None:
            for i, quote in enumerate(quotes):
                if quote.symbol == current_symbol:
                    new_index = i
                    break
        self._display_index = new_index

        # Only repaint immediately on the first successful load; otherwise let
        # the rotate timer keep its rhythm.
        if not had_quotes:
            self.window.update_quote(self._quotes[self._display_index])

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
        self.refresh_quotes()
        self.tray.show_message("添加成功", f"已添加股票代码 {normalized}")
        return True

    def remove_symbol(self, symbol: str) -> None:
        if symbol not in self.symbols:
            return
        self.symbols = [item for item in self.symbols if item != symbol]
        self.state_store.save_symbols(self.symbols)
        self._quotes = [quote for quote in self._quotes if quote.symbol != symbol]
        self.tray.update_symbols(self.get_symbol_entries())
        self._display_index = 0
        if self._quotes:
            self.window.update_quote(self._quotes[0])
        elif self.symbols:
            self.refresh_quotes()
        else:
            self.window.show_error("No symbols configured")

    def get_symbol_entries(self) -> list[tuple[str, str]]:
        names = {quote.symbol: quote.name for quote in self._quotes if quote.name}
        return [(symbol, names.get(symbol, symbol)) for symbol in self.symbols]

    def get_offsets(self) -> tuple[int, int]:
        return self.horizontal_offset, self.vertical_offset

    def get_autostart(self) -> bool:
        return self.autostart_enabled

    def get_visibility_mode(self) -> str:
        return self.visibility_mode

    def set_horizontal_offset(self, offset: int) -> None:
        self.horizontal_offset = offset
        self._apply_anchor_position()

    def set_vertical_offset(self, offset: int) -> None:
        self.vertical_offset = offset
        self._apply_anchor_position()

    def toggle_autostart(self, checked: bool) -> None:
        success = autostart.set_enabled(checked)
        if success:
            self.autostart_enabled = checked
        self.tray.set_autostart_checked(self.autostart_enabled)

    def set_visibility_mode(self, mode: str) -> None:
        if mode not in {"always", "trading_time"}:
            return
        self.visibility_mode = mode
        self.state_store.save_visibility_mode(mode)
        self.tray.set_visibility_mode(mode)
        self.refresh_quotes()

    def _apply_anchor_position(self) -> None:
        self.state_store.save_offsets(self.horizontal_offset, self.vertical_offset)
        self._apply_window_position(
            self.window.anchor_to_global(
                horizontal_offset=self.horizontal_offset,
                vertical_offset=self.vertical_offset,
            )
        )

    def _apply_window_position(self, pos: QPoint) -> None:
        self.window.move(pos)

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
        if not self._should_show_window():
            self.window.hide()
            return
        if self.window.isMinimized():
            self.window.showNormal()
        else:
            self.window.show()
        reassert_topmost(self._window_hwnd, topmost=self.settings.auto_topmost)
        self._start_topmost_burst()

    def _should_show_window(self) -> bool:
        if self.visibility_mode == "always":
            return True
        return is_market_visible(datetime.now())

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

    def check_for_update(self) -> None:
        self.update_controller.check(silent=False)

    def exit_app(self) -> None:
        pos = self.window.pos()
        self._save_position_timer.stop()
        self.state_store.save_position(pos.x(), pos.y())
        self.state_store.save_symbols(self.symbols)
        self.window.set_keep_visible_enabled(False)
        self._topmost_burst_timer.stop()
        self.refresh_timer.stop()
        self.rotate_timer.stop()
        self.update_check_timer.stop()
        if self._quote_worker is not None and self._quote_worker.isRunning():
            # Wait long enough to cover the network timeout so we never destroy
            # a still-running QThread during interpreter teardown.
            if not self._quote_worker.wait(9000):
                logger.warning("Quote worker did not finish before exit")
        self.api.close()
        self.update_controller.shutdown()
        self._foreground_watchdog.stop()
        self.tray.hide()
        self.qt_app.quit()

    def run(self) -> int:
        logger.info("StockMonitor started")
        return self.qt_app.exec()
