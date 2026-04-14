from __future__ import annotations

import httpx
from loguru import logger

from stockmonitor.models.quote import StockQuote


class StockAPI:
    TENCENT_URL = "https://qt.gtimg.cn/q="
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        )
    }

    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    def fetch_quotes(self, symbols: list[str]) -> list[StockQuote]:
        if not symbols:
            return []
        return self._fetch_tencent_quotes(symbols)

    def validate_symbol(self, symbol: str) -> bool:
        quotes = self.fetch_quotes([symbol])
        return any(quote.symbol == symbol for quote in quotes)

    def _fetch_tencent_quotes(self, symbols: list[str]) -> list[StockQuote]:
        market_symbols = [self._to_tencent_symbol(symbol) for symbol in symbols]
        url = f"{self.TENCENT_URL}{','.join(market_symbols)}"
        logger.debug("Fetching quotes from Tencent: {}", url)

        with httpx.Client(timeout=self.timeout, headers=self.DEFAULT_HEADERS) as client:
            response = client.get(url)
            response.raise_for_status()
            text = response.text

        quotes: list[StockQuote] = []
        lines = [line.strip() for line in text.split(";") if line.strip()]
        for line in lines:
            if '="' not in line:
                continue
            prefix, raw_payload = line.split('="', 1)
            payload = raw_payload.rstrip('"')
            fields = payload.split("~")
            if len(fields) < 33:
                continue

            market_symbol = prefix.split("_", 1)[-1]
            symbol = market_symbol[2:] if len(market_symbol) > 2 else market_symbol
            name = fields[1] or symbol

            try:
                price = float(fields[3])
                change_percent = float(fields[32])
            except ValueError:
                continue

            quotes.append(
                StockQuote(
                    symbol=symbol,
                    name=name,
                    price=price,
                    change_percent=change_percent,
                    source="tencent",
                )
            )

        return quotes

    @staticmethod
    def _to_tencent_symbol(symbol: str) -> str:
        normalized = symbol.strip().lower()
        if normalized.startswith(("sh", "sz")):
            return normalized
        if normalized.startswith(("6", "5", "9")):
            return f"sh{normalized}"
        if normalized.startswith(("0", "2", "3")):
            return f"sz{normalized}"
        return f"sz{normalized}"
