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

    def load_position(self) -> tuple[int, int] | None:
        try:
            data = self._load_data()
            x = int(data.get("x"))
            y = int(data.get("y"))
            return x, y
        except Exception as exc:
            logger.warning("Failed to load window state: {}", exc)
            return None

    def load_symbols(self) -> list[str] | None:
        data = self._load_data()
        symbols = data.get("symbols")
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

    def load_alignment(self) -> tuple[str, str] | None:
        data = self._load_data()
        horizontal_align = data.get("horizontal_align")
        vertical_align = data.get("vertical_align")
        if not isinstance(horizontal_align, str) or not isinstance(vertical_align, str):
            return None
        return horizontal_align, vertical_align

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
        try:
            data = self._load_data()
            data.update(
                {
                    "horizontal_offset": horizontal_offset,
                    "vertical_offset": vertical_offset,
                }
            )
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to save offsets state: {}", exc)

    def load_autostart(self) -> bool | None:
        data = self._load_data()
        value = data.get("autostart")
        if isinstance(value, bool):
            return value
        return None

    def save_autostart(self, enabled: bool) -> None:
        try:
            data = self._load_data()
            data.update({"autostart": enabled})
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to save autostart state: {}", exc)

    def save_position(self, x: int, y: int) -> None:
        try:
            data = self._load_data()
            data.update({"x": x, "y": y, "position_mode": "manual"})
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to save window state: {}", exc)

    def save_alignment(self, horizontal_align: str, vertical_align: str) -> None:
        try:
            data = self._load_data()
            data.update(
                {
                    "horizontal_align": horizontal_align,
                    "vertical_align": vertical_align,
                    "position_mode": "anchor",
                }
            )
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to save alignment state: {}", exc)

    def save_symbols(self, symbols: list[str]) -> None:
        try:
            data = self._load_data()
            data.update({"symbols": symbols})
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to save symbols state: {}", exc)
