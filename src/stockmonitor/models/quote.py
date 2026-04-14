from pydantic import BaseModel


class StockQuote(BaseModel):
    symbol: str
    name: str
    price: float
    change_percent: float
    source: str = "unknown"
