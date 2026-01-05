"""Shared fixtures for algo_trader system tests.

These fixtures support deterministic e2e tests without external services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Protocol

import pytest

from system.algo_trader.domain.events import DecisionEvent, OverrideEvent
from system.algo_trader.domain.models import Bar, Quote


@dataclass(slots=True)
class FixedClock:
    """Clock with fixed timestamp for deterministic tests."""

    now_ts: datetime

    def now(self) -> datetime:
        """Return fixed time."""
        return self.now_ts


@dataclass(slots=True)
class InMemoryJournal:
    """Journal that stores all recorded events in-memory."""

    decisions: list[DecisionEvent] = field(default_factory=list)
    overrides: list[OverrideEvent] = field(default_factory=list)

    def record_decision(self, event: DecisionEvent) -> None:
        """Record a decision event."""
        self.decisions.append(event)

    def record_override(self, event: OverrideEvent) -> None:
        """Record an override event."""
        self.overrides.append(event)

    def record_fill(self, fill) -> None:  # Engine optional extension point
        """Record fills (ignored for these tests)."""
        _ = fill


@dataclass(slots=True)
class FakeMarketData:
    """Market data adapter that returns a scripted quote sequence."""

    quotes_by_call: list[dict[str, Quote]]
    i: int = 0

    def get_quotes(self, symbols):
        """Return the next quotes snapshot."""
        _ = symbols
        if self.i >= len(self.quotes_by_call):
            return self.quotes_by_call[-1]
        q = self.quotes_by_call[self.i]
        self.i += 1
        return q

    def get_daily_bars(self, symbols, start, end):
        """Unused in these tests."""
        _ = (symbols, start, end)
        return []


@dataclass(slots=True)
class FakeRedisBroker:
    """Redis broker adapter stub (no overrides)."""

    def poll_overrides(self, max_items: int = 10):
        _ = max_items
        return []

    def publish_market(self, events):
        _ = events

    def publish_decision(self, event):
        _ = event

    def publish_override(self, event):
        _ = event


class RuntimeConfigPort(Protocol):
    """Subset of runtime config used by ForwardTestApp."""

    def get_watchlist(self, engine_id: str, limit: int = 200) -> list[str]: ...

    def get_poll_seconds(self, engine_id: str, default: float = 2.0) -> float: ...


@dataclass(slots=True)
class FakeRuntimeConfig(RuntimeConfigPort):
    """Simple runtime config implementation with counters."""

    watchlist: list[str]
    poll_seconds: float = 0.0
    watchlist_calls: int = 0
    poll_calls: int = 0

    def get_watchlist(self, engine_id: str, limit: int = 200) -> list[str]:
        _ = engine_id
        self.watchlist_calls += 1
        return list(self.watchlist)[:limit]

    def get_poll_seconds(self, engine_id: str, default: float = 2.0) -> float:
        _ = (engine_id, default)
        self.poll_calls += 1
        return float(self.poll_seconds)

    def set_poll_seconds(
        self, engine_id: str, poll_seconds: float, ttl_seconds: int | None = None
    ) -> None:
        _ = (engine_id, ttl_seconds)
        self.poll_seconds = float(poll_seconds)


@pytest.fixture
def t0() -> datetime:
    """Return a shared fixed epoch time."""
    return datetime(2024, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def fixed_clock(t0: datetime) -> FixedClock:
    """Provide a fixed clock."""
    return FixedClock(now_ts=t0)


@pytest.fixture
def in_memory_journal() -> InMemoryJournal:
    """Provide an in-memory journal."""
    return InMemoryJournal()


@pytest.fixture
def fake_redis_broker() -> FakeRedisBroker:
    """Provide a fake redis broker."""
    return FakeRedisBroker()


@pytest.fixture
def fake_runtime_config() -> FakeRuntimeConfig:
    """Provide default runtime config with an AAPL watchlist."""
    return FakeRuntimeConfig(watchlist=["AAPL"], poll_seconds=0.0)


@pytest.fixture
def mk_bars():
    """Factory: build daily bars from a price series."""

    def _mk(symbol: str, start_day: date, prices: list[int]) -> list[Bar]:
        out: list[Bar] = []
        for i, p in enumerate(prices):
            d = start_day + timedelta(days=i)
            px = Decimal(str(p))
            out.append(
                Bar(
                    symbol=symbol,
                    day=d,
                    open=px,
                    high=px,
                    low=px,
                    close=px,
                    volume=1000,
                )
            )
        return out

    return _mk

