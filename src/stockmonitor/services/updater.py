from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx
from loguru import logger

from stockmonitor import __version__

GITHUB_OWNER = "DarlingCY"
GITHUB_REPO = "StockMonitor"
# Use the public releases page (redirects to /tag/vX.Y.Z), not the REST API —
# unauthenticated api.github.com is capped at ~60 req/hour/IP and breaks update checks.
LATEST_RELEASE_PAGE = (
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
ASSET_NAME = "StockMonitor-Setup.exe"
_TAG_IN_URL = re.compile(r"/releases/tag/([^/?#]+)")

_HEADERS = {
    "User-Agent": f"{GITHUB_REPO}/{__version__}",
    "Accept": "text/html,application/xhtml+xml",
}


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag_name: str
    download_url: str
    html_url: str
    notes: str


def _parse_version(value: str) -> tuple[int, ...]:
    """Parse a version string like 'v1.2.3' / '1.2.3' into a comparable tuple."""
    cleaned = value.strip().lstrip("vV")
    # Drop any pre-release / build metadata suffix (e.g. 1.2.3-dev, 1.2.3+abc).
    cleaned = re.split(r"[-+]", cleaned, maxsplit=1)[0]
    parts: list[int] = []
    for chunk in cleaned.split("."):
        match = re.match(r"\d+", chunk)
        parts.append(int(match.group()) if match else 0)
    return tuple(parts) if parts else (0,)


def is_newer(remote: str, local: str) -> bool:
    """Return True when the remote version is strictly newer than local."""
    remote_parts = _parse_version(remote)
    local_parts = _parse_version(local)
    length = max(len(remote_parts), len(local_parts))
    remote_parts += (0,) * (length - len(remote_parts))
    local_parts += (0,) * (length - len(local_parts))
    return remote_parts > local_parts


def current_version() -> str:
    return __version__


def fetch_latest_release(timeout: float = 10.0) -> ReleaseInfo | None:
    """Resolve the latest GitHub release via the public /releases/latest redirect."""
    try:
        with httpx.Client(
            timeout=timeout, headers=_HEADERS, follow_redirects=True
        ) as client:
            response = client.get(LATEST_RELEASE_PAGE)
            response.raise_for_status()
            final_url = str(response.url)
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch latest release: {}", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - never let update check crash app
        logger.warning("Unexpected error fetching latest release: {}", exc)
        return None

    match = _TAG_IN_URL.search(final_url)
    if not match:
        logger.warning("Could not parse release tag from {}", final_url)
        return None

    tag_name = match.group(1).strip()
    if not tag_name:
        logger.warning("Latest release has empty tag_name")
        return None

    html_url = (
        f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tag/{tag_name}"
    )
    download_url = (
        f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/"
        f"{tag_name}/{ASSET_NAME}"
    )
    return ReleaseInfo(
        version=tag_name.lstrip("vV"),
        tag_name=tag_name,
        download_url=download_url,
        html_url=html_url,
        notes="",
    )


def check_for_update(timeout: float = 10.0) -> ReleaseInfo | None:
    """Return the release info if a newer version is available, else None."""
    release = fetch_latest_release(timeout=timeout)
    if release is None:
        return None
    if is_newer(release.version, __version__):
        logger.info(
            "Update available: {} (current {})", release.version, __version__
        )
        return release
    logger.info("No update available (current {})", __version__)
    return None


def download_installer(
    release: ReleaseInfo,
    progress_callback=None,
    cancel_check=None,
    timeout: float = 60.0,
) -> Path | None:
    """Download the installer asset to a temp file. Returns the path or None.

    progress_callback receives (downloaded_bytes, total_bytes).
    cancel_check is an optional callable returning True to abort the download.
    """
    if not release.download_url:
        logger.warning("Release {} has no installer asset", release.version)
        return None

    target_dir = Path(tempfile.gettempdir())
    target_path = target_dir / f"StockMonitor-Setup-{release.version}.exe"

    try:
        with httpx.Client(
            timeout=timeout, headers=_HEADERS, follow_redirects=True
        ) as client:
            with client.stream("GET", release.download_url) as response:
                response.raise_for_status()
                total = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                with open(target_path, "wb") as handle:
                    for chunk in response.iter_bytes(chunk_size=65536):
                        if cancel_check is not None and cancel_check():
                            logger.info("Installer download cancelled by user")
                            handle.close()
                            _safe_unlink(target_path)
                            return None
                        handle.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback is not None:
                            progress_callback(downloaded, total)
    except httpx.HTTPError as exc:
        logger.error("Installer download failed: {}", exc)
        _safe_unlink(target_path)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected installer download error: {}", exc)
        _safe_unlink(target_path)
        return None

    logger.info("Installer downloaded to {}", target_path)
    return target_path


def launch_installer(installer_path: Path) -> bool:
    """Launch the installer after this process has fully exited.

    Starts a detached waiter that polls until the current PID disappears,
    then runs the installer. That way Inno Setup can replace locked files.
    """
    if not installer_path.exists():
        logger.error("Installer not found: {}", installer_path)
        return False

    installer = str(installer_path.resolve())
    try:
        if sys.platform != "win32":
            subprocess.Popen([installer])  # noqa: S603
            return True

        pid = os.getpid()
        bat_path = Path(tempfile.gettempdir()) / f"stockmonitor-update-{pid}.bat"
        bat_path.write_text(
            "\r\n".join(
                [
                    "@echo off",
                    "setlocal",
                    f":wait",
                    f'tasklist /FI "PID eq {pid}" 2>nul | find "{pid}" >nul',
                    "if not errorlevel 1 (",
                    "  timeout /t 1 /nobreak >nul",
                    "  goto wait",
                    ")",
                    # Brief settle so file locks are released.
                    "timeout /t 1 /nobreak >nul",
                    f'start "" "{installer}"',
                    'del "%~f0" >nul 2>&1',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        # Detach the waiter so it outlives this process; CREATE_NO_WINDOW
        # keeps the polling console invisible.
        creationflags = (
            getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            | 0x08000000  # CREATE_NO_WINDOW
        )
        subprocess.Popen(  # noqa: S603
            ["cmd.exe", "/c", str(bat_path)],
            creationflags=creationflags,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(
            "Scheduled installer {} to run after PID {} exits", installer, pid
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to launch installer: {}", exc)
        return False


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
