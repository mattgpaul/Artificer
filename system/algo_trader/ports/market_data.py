from __future__ import annotations

from datetime import date
from typing import Protocol, Sequence

from system.algo_trader.domain.models import Bar, Quote


class MarketDataPort(Protocol):
    def get_daily_bars(self, symbols: Sequence[str], start: date, end: date) -> Sequence[Bar]: ...

    def get_quotes(self, symbols: Sequence[str]) -> dict[str, Quote]: ...

