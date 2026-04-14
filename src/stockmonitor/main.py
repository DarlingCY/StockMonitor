from __future__ import annotations

import sys

from loguru import logger

from stockmonitor.app import StockMonitorApp
from stockmonitor.config.settings import Settings


def main() -> int:
    settings = Settings()
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(
        settings.log_file,
        level="INFO",
        rotation="1 MB",
        retention=5,
        encoding="utf-8",
    )
    app = StockMonitorApp(settings)
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
