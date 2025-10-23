from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, field_validator


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

    @field_validator("start", "end")
    @classmethod
    def convert_to_utc(cls, v: Any) -> datetime:
        """Convert datetime to UTC if it has timezone info"""
        if isinstance(v, datetime):
            if v.tzinfo is not None:
                return v.astimezone(timezone.utc)
            else:
                # If naive, assume it's EST and convert to UTC
                # EST is UTC-5, EDT is UTC-4 - you might need pytz for proper handling
                from zoneinfo import ZoneInfo  # Python 3.9+

                est = ZoneInfo("America/New_York")  # Handles EST/EDT automatically
                return v.replace(tzinfo=est).astimezone(timezone.utc)
        return v
