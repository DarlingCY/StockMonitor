import json
from pathlib import Path

from loguru import logger


class StateStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load_data(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load state file: {}", exc)
            return {}

    def _update(self, **fields) -> None:
        try:
            data = self._load_data()
            data.update(fields)
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to save state: {}", exc)

    def load_position(self) -> tuple[int, int] | None:
        try:
            data = self._load_data()
            return int(data["x"]), int(data["y"])
        except Exception as exc:
            logger.warning("Failed to load window state: {}", exc)
            return None

    def load_symbols(self) -> list[str] | None:
        symbols = self._load_data().get("symbols")
        if not isinstance(symbols, list):
            return None
        cleaned = [
            str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()
        ]
        return cleaned or None

    def load_position_mode(self) -> str | None:
        data = self._load_data()
        mode = data.get("position_mode")
        if mode in {"manual", "anchor"}:
            return mode
        if "x" in data and "y" in data:
            return "manual"
        return None

    def load_offsets(self) -> tuple[int, int] | None:
        data = self._load_data()
        horizontal_offset = data.get("horizontal_offset")
        vertical_offset = data.get("vertical_offset")
        if horizontal_offset is None or vertical_offset is None:
            return None
        try:
            return int(horizontal_offset), int(vertical_offset)
        except (ValueError, TypeError):
            return None

    def save_offsets(self, horizontal_offset: int, vertical_offset: int) -> None:
        self._update(
            horizontal_offset=horizontal_offset,
            vertical_offset=vertical_offset,
        )

    def load_visibility_mode(self) -> str | None:
        mode = self._load_data().get("visibility_mode")
        if mode in {"always", "trading_time"}:
            return mode
        return None

    def save_visibility_mode(self, mode: str) -> None:
        if mode not in {"always", "trading_time"}:
            return
        self._update(visibility_mode=mode)

    def save_position(self, x: int, y: int) -> None:
        self._update(x=x, y=y, position_mode="manual")

    def save_symbols(self, symbols: list[str]) -> None:
        self._update(symbols=symbols)
