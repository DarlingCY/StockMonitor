from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QProgressDialog,
)

from stockmonitor.services import updater
from stockmonitor.services.updater import ReleaseInfo


class _CheckWorker(QThread):
    finished_check = Signal(object)  # ReleaseInfo | None

    def run(self) -> None:
        result = updater.check_for_update()
        self.finished_check.emit(result)


class _DownloadWorker(QThread):
    progress = Signal(int, int)  # downloaded, total
    finished_download = Signal(object)  # Path | None

    def __init__(self, release: ReleaseInfo, parent=None) -> None:
        super().__init__(parent)
        self._release = release
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self) -> None:
        path = updater.download_installer(
            self._release,
            progress_callback=lambda d, t: self.progress.emit(d, t),
            cancel_check=self._cancel_event.is_set,
        )
        self.finished_download.emit(path)


class UpdateController(QObject):
    """Coordinates update checks/downloads and user-facing dialogs.

    Runs network work on background threads to keep the UI responsive.
    Automatic (silent) checks only raise a tray notification; the modal
    install prompt is shown for manual checks or when the user opts in.
    """

    def __init__(self, notify=None, request_exit=None, parent=None) -> None:
        super().__init__(parent)
        self._notify = notify  # callable(title, message) for tray balloons
        self._request_exit = request_exit  # callable() for full app shutdown
        self._check_worker: _CheckWorker | None = None
        self._download_worker: _DownloadWorker | None = None
        self._progress_dialog: QProgressDialog | None = None
        # Guards the whole flow (check -> prompt -> download -> install).
        self._busy = False
        self._pending_release: ReleaseInfo | None = None

    def check(self, *, silent: bool) -> None:
        """Start a background update check.

        silent=True (automatic startup/daily checks): on a new version, only a
        tray notification is shown; no modal popups, no "up to date" popup.
        silent=False (manual): shows result/install dialogs.
        """
        if self._busy:
            # An update flow is already in progress. For a manual re-check,
            # re-surface any pending release prompt instead of stacking checks.
            if not silent and self._pending_release is not None:
                self._prompt_update(self._pending_release)
            return
        self._busy = True
        worker = _CheckWorker()
        worker.finished_check.connect(
            lambda release: self._on_check_finished(release, silent)
        )
        worker.finished.connect(self._clear_check_worker)
        worker.finished.connect(worker.deleteLater)
        self._check_worker = worker
        worker.start()

    @Slot()
    def _clear_check_worker(self) -> None:
        self._check_worker = None

    def _on_check_finished(self, release: ReleaseInfo | None, silent: bool) -> None:
        if release is None:
            self._busy = False
            if not silent:
                QMessageBox.information(
                    None,
                    "检查更新",
                    f"当前已是最新版本（v{updater.current_version()}）。",
                )
            return

        self._pending_release = release
        if silent:
            # Automatic check: notify only; user installs via tray menu.
            self._busy = False
            if self._notify is not None:
                self._notify(
                    "发现新版本",
                    f"StockMonitor v{release.version} 可用，"
                    "点击托盘菜单“检查更新”进行升级。",
                )
            return
        self._prompt_update(release)

    def _prompt_update(self, release: ReleaseInfo) -> None:
        self._busy = True
        notes = release.notes.strip()
        if len(notes) > 500:
            notes = notes[:500] + "…"
        detail = f"\n\n更新说明：\n{notes}" if notes else ""

        box = QMessageBox()
        box.setWindowTitle("发现新版本")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(
            f"发现新版本 v{release.version}（当前 v{updater.current_version()}）。\n"
            f"是否立即下载并安装？{detail}"
        )
        download_btn = box.addButton("下载并安装", QMessageBox.ButtonRole.AcceptRole)
        page_btn = box.addButton("前往发布页", QMessageBox.ButtonRole.ActionRole)
        box.addButton("稍后", QMessageBox.ButtonRole.RejectRole)
        box.exec()

        clicked = box.clickedButton()
        if clicked is download_btn:
            if release.download_url:
                self._start_download(release)
            else:
                self._open_release_page(release)
                self._busy = False
        elif clicked is page_btn:
            self._open_release_page(release)
            self._busy = False
        else:
            # "稍后": keep _pending_release so a manual re-check re-prompts.
            self._busy = False

    def _open_release_page(self, release: ReleaseInfo) -> None:
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        url = release.html_url or (
            f"https://github.com/{updater.GITHUB_OWNER}/"
            f"{updater.GITHUB_REPO}/releases/latest"
        )
        QDesktopServices.openUrl(QUrl(url))

    def _start_download(self, release: ReleaseInfo) -> None:
        if self._download_worker is not None and self._download_worker.isRunning():
            return

        dialog = QProgressDialog("正在下载更新…", "取消", 0, 100)
        dialog.setWindowTitle("下载更新")
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setMinimumDuration(0)
        dialog.setValue(0)
        self._progress_dialog = dialog

        worker = _DownloadWorker(release)
        worker.progress.connect(self._on_download_progress)
        worker.finished_download.connect(self._on_download_finished)
        worker.finished.connect(self._clear_download_worker)
        worker.finished.connect(worker.deleteLater)
        dialog.canceled.connect(worker.cancel)
        self._download_worker = worker
        worker.start()

    @Slot()
    def _clear_download_worker(self) -> None:
        self._download_worker = None

    @Slot(int, int)
    def _on_download_progress(self, downloaded: int, total: int) -> None:
        if self._progress_dialog is None:
            return
        if total > 0:
            percent = int(downloaded * 100 / total)
            self._progress_dialog.setValue(min(percent, 100))
            mb_done = downloaded / 1024 / 1024
            mb_total = total / 1024 / 1024
            self._progress_dialog.setLabelText(
                f"正在下载更新… {mb_done:.1f} / {mb_total:.1f} MB"
            )
        else:
            mb_done = downloaded / 1024 / 1024
            self._progress_dialog.setLabelText(f"正在下载更新… {mb_done:.1f} MB")

    def _on_download_finished(self, installer_path) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.close()
            self._progress_dialog = None

        if installer_path is None:
            # Either failure or user cancellation; release the flow guard.
            self._busy = False
            QMessageBox.warning(
                None,
                "下载未完成",
                "更新下载失败或已取消，可稍后重试或前往发布页手动下载。",
            )
            return

        proceed = QMessageBox.question(
            None,
            "准备安装",
            "下载完成。将关闭 StockMonitor 并启动安装程序，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if proceed != QMessageBox.StandardButton.Yes:
            self._busy = False
            return

        if updater.launch_installer(installer_path):
            # Full shutdown (timers/threads/tray/watchdog), not bare quit —
            # otherwise StockMonitor.exe stays locked and the installer fails.
            if self._request_exit is not None:
                self._request_exit()
            else:
                QApplication.quit()
        else:
            self._busy = False
            QMessageBox.warning(
                None,
                "启动失败",
                "无法启动安装程序，请前往临时目录手动运行。",
            )

    def shutdown(self) -> None:
        """Cancel and wait for in-flight workers during app exit."""
        download = self._download_worker
        if download is not None and download.isRunning():
            download.cancel()
            download.wait(3000)
        check = self._check_worker
        if check is not None and check.isRunning():
            check.wait(2000)
