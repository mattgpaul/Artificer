from datetime import datetime
from pydantic import BaseModel

class StockQuote(BaseModel):
    price: float
    bid: float
    ask: float
    volume: int
    change: float
    change_pct: float
    timestamp: int

class MarketHours(BaseModel):
    date: datetime
    start: datetime
    end: datetime