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
LATEST_RELEASE_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
ASSET_NAME = "StockMonitor-Setup.exe"

_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": f"{GITHUB_REPO}/{__version__}",
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
    """Query the GitHub latest release. Returns None on any failure."""
    try:
        with httpx.Client(
            timeout=timeout, headers=_HEADERS, follow_redirects=True
        ) as client:
            response = client.get(LATEST_RELEASE_URL)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch latest release: {}", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - never let update check crash app
        logger.warning("Unexpected error fetching latest release: {}", exc)
        return None

    tag_name = str(data.get("tag_name") or "").strip()
    if not tag_name:
        logger.warning("Latest release has no tag_name")
        return None

    download_url = ""
    for asset in data.get("assets") or []:
        if str(asset.get("name", "")).strip() == ASSET_NAME:
            download_url = str(asset.get("browser_download_url") or "")
            break

    return ReleaseInfo(
        version=tag_name.lstrip("vV"),
        tag_name=tag_name,
        download_url=download_url,
        html_url=str(data.get("html_url") or ""),
        notes=str(data.get("body") or ""),
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
    """Start the installer and signal the app should exit so it can replace files.

    Returns True if the installer was launched successfully.
    """
    if not installer_path.exists():
        logger.error("Installer not found: {}", installer_path)
        return False
    try:
        # Detach the installer so it survives this process exiting.
        if sys.platform == "win32":
            os.startfile(str(installer_path))  # noqa: S606 - trusted local installer
        else:
            subprocess.Popen([str(installer_path)])  # noqa: S603
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
