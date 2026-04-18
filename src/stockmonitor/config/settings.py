from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    symbols: str = "600519,000001,300750"
    refresh_interval_seconds: int = 15
    horizontal_align: str = "center"
    vertical_align: str = "bottom"
    horizontal_offset: int = 0
    vertical_offset: int = 0
    auto_topmost: bool = True
    background_color: str = "rgba(24, 24, 24, 220)"

    model_config = SettingsConfigDict(
        env_file=str(Path.home() / ".StockMonitor" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def symbols_list(self) -> list[str]:
        return [s.strip().upper() for s in self.symbols.split(",") if s.strip()]

    @property
    def normalized_horizontal_align(self) -> str:
        value = self.horizontal_align.strip().lower()
        return value if value in {"left", "center", "right"} else "left"

    @property
    def normalized_vertical_align(self) -> str:
        value = self.vertical_align.strip().lower()
        return value if value in {"top", "center", "bottom"} else "top"

    @property
    def app_dir(self) -> Path:
        path = Path.home() / ".StockMonitor"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def state_file(self) -> Path:
        return self.app_dir / "state.json"

    @property
    def log_dir(self) -> Path:
        path = self.app_dir / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def log_file(self) -> Path:
        return self.log_dir / "stockmonitor.log"
