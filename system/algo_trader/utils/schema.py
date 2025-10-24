"""Pydantic schemas for market data validation.

This module provides Pydantic models for validating stock quotes, market hours,
and other market-related data structures with automatic timezone handling and
field validation.
"""

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, field_validator


class StockQuote(BaseModel):
    """Real-time stock quote data model.

    Represents a snapshot of current stock pricing and volume information
    from market data feeds.
    """

    price: float
    bid: float
    ask: float
    volume: int
    change: float
    change_pct: float
    timestamp: int


class MarketHours(BaseModel):
    """Market hours information for a trading day.

    Contains start and end times for standard market hours, with timezone
    validation to ensure all timestamps are timezone-aware.
    """

    date: datetime
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def convert_to_utc(cls, v: Any) -> datetime:
        """Convert datetime to UTC if it has timezone info."""
        if isinstance(v, datetime):
            if v.tzinfo is not None:
                return v.astimezone(timezone.utc)
            else:
                # If naive, assume it's EST and convert to UTC
                # EST is UTC-5, EDT is UTC-4 - ZoneInfo handles EST/EDT automatically
                est = ZoneInfo("America/New_York")
                return v.replace(tzinfo=est).astimezone(timezone.utc)
        return v
