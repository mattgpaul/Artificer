from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from system.algo_trader.domain.models import Bar, Quote
from system.algo_trader.ports.market_data import MarketDataPort
from system.algo_trader.schwab.market_handler import MarketHandler
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


def _to_date(ms_epoch: int) -> date:
    return datetime.fromtimestamp(ms_epoch / 1000.0, tz=timezone.utc).date()


def _to_dt(ms_epoch: int) -> datetime:
    return datetime.fromtimestamp(ms_epoch / 1000.0, tz=timezone.utc)


@dataclass(slots=True)
class SchwabMarketDataAdapter(MarketDataPort):
    """Adapter around the existing Schwab MarketHandler."""

    client: MarketHandler

    def get_daily_bars(self, symbols: Sequence[str], start: date, end: date) -> Sequence[Bar]:
        out: list[Bar] = []
        for sym in symbols:
            data = self.client.get_price_history(
                sym,
                period_type=PeriodType.YEAR,
                period=1,
                frequency_type=FrequencyType.DAILY,
                frequency=1,
            )
            candles = data.get("candles", []) if isinstance(data, dict) else []
            for c in candles:
                day = _to_date(int(c.get("datetime")))
                if day < start or day > end:
                    continue
                out.append(
                    Bar(
                        symbol=sym,
                        day=day,
                        open=Decimal(str(c.get("open"))),
                        high=Decimal(str(c.get("high"))),
                        low=Decimal(str(c.get("low"))),
                        close=Decimal(str(c.get("close"))),
                        volume=int(c.get("volume") or 0),
                    )
                )
        out.sort(key=lambda b: (b.day, b.symbol))
        return out

    def get_quotes(self, symbols: Sequence[str]) -> dict[str, Quote]:
        raw = self.client.get_quotes(list(symbols))
        out: dict[str, Quote] = {}
        for sym, q in raw.items():
            ts_raw = q.get("timestamp")
            ts = _to_dt(int(ts_raw)) if ts_raw is not None else datetime.now(tz=timezone.utc)
            out[sym] = Quote(
                symbol=sym,
                ts=ts,
                price=Decimal(str(q.get("price") or "0")),
                bid=None if q.get("bid") is None else Decimal(str(q.get("bid"))),
                ask=None if q.get("ask") is None else Decimal(str(q.get("ask"))),
                volume=None if q.get("volume") is None else int(q.get("volume")),
            )
        return out
