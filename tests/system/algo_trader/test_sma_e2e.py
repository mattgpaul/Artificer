from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from system.algo_trader.adapters.paper.broker import PaperBroker
from system.algo_trader.apps.backtest_app import BacktestApp
from system.algo_trader.apps.forward_app import ForwardTestApp
from system.algo_trader.domain.engine import Engine
from system.algo_trader.domain.events import DecisionEvent, OverrideEvent
from system.algo_trader.domain.models import Bar, Quote
from system.algo_trader.domain.portfolio import SimplePortfolio
from system.algo_trader.domain.strategies import SmaCrossoverStrategy


@dataclass(slots=True)
class FixedClock:
    now_ts: datetime

    def now(self) -> datetime:
        return self.now_ts


@dataclass(slots=True)
class InMemoryJournal:
    decisions: list[DecisionEvent] = field(default_factory=list)
    overrides: list[OverrideEvent] = field(default_factory=list)

    def record_decision(self, event: DecisionEvent) -> None:
        self.decisions.append(event)

    def record_override(self, event: OverrideEvent) -> None:
        self.overrides.append(event)

    def record_fill(self, fill) -> None:  # Engine optional extension point
        _ = fill


@dataclass(slots=True)
class FakeMarketData:
    quotes_by_call: list[dict[str, Quote]]
    i: int = 0

    def get_quotes(self, symbols):
        _ = symbols
        if self.i >= len(self.quotes_by_call):
            return self.quotes_by_call[-1]
        q = self.quotes_by_call[self.i]
        self.i += 1
        return q

    def get_daily_bars(self, symbols, start, end):
        _ = (symbols, start, end)
        return []


@dataclass(slots=True)
class FakeRedisBroker:
    def poll_overrides(self, max_items: int = 10):
        _ = max_items
        return []

    def publish_market(self, events):
        _ = events

    def publish_decision(self, event):
        _ = event

    def publish_override(self, event):
        _ = event


def _mk_bars(symbol: str, start_day: date, prices: list[int]) -> list[Bar]:
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


def test_sma_20_10_backtest_e2e_places_buy_then_sell():
    sym = "AAPL"
    start = date(2024, 1, 1)

    # Construct a series: flat then up then down (long enough) to trigger both cross-up and cross-down.
    prices = [100] * 30 + list(range(101, 161)) + list(range(160, 60, -1))
    bars = _mk_bars(sym, start, prices)

    clock = FixedClock(now_ts=datetime(2024, 1, 1, tzinfo=timezone.utc))
    journal = InMemoryJournal()
    portfolio = SimplePortfolio()
    strategy = SmaCrossoverStrategy(window_a=20, window_b=10)
    engine = Engine(clock=clock, strategy=strategy, portfolio=portfolio, journal=journal)

    broker = PaperBroker()
    app = BacktestApp(engine=engine, broker=broker, bars=bars)
    app.run()

    intents = [i for d in journal.decisions for i in d.order_intents]
    assert any(i.side.value == "BUY" for i in intents)
    assert any(i.side.value == "SELL" for i in intents)
    assert portfolio.position(sym) == 0


def test_sma_20_10_forward_test_e2e_paper_trades_on_quotes():
    sym = "AAPL"
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)

    prices = [100] * 30 + list(range(101, 161)) + list(range(160, 60, -1))
    quotes = [
        {sym: Quote(symbol=sym, ts=t0 + timedelta(seconds=i), price=Decimal(str(p)))}
        for i, p in enumerate(prices)
    ]

    market = FakeMarketData(quotes_by_call=quotes)
    redis_broker = FakeRedisBroker()
    broker = PaperBroker()

    clock = FixedClock(now_ts=t0)
    journal = InMemoryJournal()
    portfolio = SimplePortfolio()
    strategy = SmaCrossoverStrategy(window_a=20, window_b=10)
    engine = Engine(clock=clock, strategy=strategy, portfolio=portfolio, journal=journal)

    app = ForwardTestApp(
        engine=engine,
        market_data=market,
        broker=broker,
        redis_broker=redis_broker,
        poll_seconds=0.0,
        symbols=[sym],
        max_iterations=len(quotes),
    )
    app.run_forever()

    intents = [i for d in journal.decisions for i in d.order_intents]
    assert any(i.side.value == "BUY" for i in intents)
    assert any(i.side.value == "SELL" for i in intents)
