from pydantic import BaseModel

class StockQuote(BaseModel):
    price: float
    bid: float
    ask: float
    volume: int
    change: float
    change_pct: float
    timestamp: int

class StockHistorical(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: int