"""End-to-end tests for algo_trader SMA strategy + portfolio risk controls.

Tests cover:
- SMA (20/10) backtest + forward-test using paper fills
- operator override side effects (set_poll_seconds)
- portfolio risk controls (max drawdown flatten/pause, sizing resize)

All external dependencies are mocked; shared helpers live in conftest.py.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from system.algo_trader.adapters.paper.broker import PaperBroker
from system.algo_trader.apps.backtest_app import BacktestApp
from system.algo_trader.apps.forward_app import ForwardTestApp
from system.algo_trader.cli.override_cli import apply_runtime_side_effects
from system.algo_trader.domain.engine import Engine
from system.algo_trader.domain.events import DecisionEvent, MarketEvent, OverrideEvent
from system.algo_trader.domain.models import Bar, OrderIntent, Quote, Side
from system.algo_trader.domain.portfolio import SimplePortfolio
from system.algo_trader.domain.strategies import SmaCrossoverStrategy

def test_sma_20_10_backtest_e2e_places_buy_then_sell(mk_bars, fixed_clock, in_memory_journal):
    sym = "AAPL"
    start = date(2024, 1, 1)

    # Construct a series: flat then up then down (long enough) to trigger both cross-up and cross-down.
    prices = [100] * 30 + list(range(101, 161)) + list(range(160, 60, -1))
    bars = mk_bars(sym, start, prices)

    clock = fixed_clock
    journal = in_memory_journal
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


def test_sma_20_10_forward_test_e2e_paper_trades_on_quotes(
    t0, fake_redis_broker, fake_runtime_config, in_memory_journal, fixed_clock
):
    sym = "AAPL"

    prices = [100] * 30 + list(range(101, 161)) + list(range(160, 60, -1))
    quotes = [
        {sym: Quote(symbol=sym, ts=t0 + timedelta(seconds=i), price=Decimal(str(p)))}
        for i, p in enumerate(prices)
    ]

    from tests.system.algo_trader.conftest import FakeMarketData  # local test helper

    market = FakeMarketData(quotes_by_call=quotes)
    redis_broker = fake_redis_broker
    broker = PaperBroker()

    clock = fixed_clock
    journal = in_memory_journal
    portfolio = SimplePortfolio()
    strategy = SmaCrossoverStrategy(window_a=20, window_b=10)
    engine = Engine(clock=clock, strategy=strategy, portfolio=portfolio, journal=journal)

    runtime = fake_runtime_config
    runtime.watchlist = [sym]
    app = ForwardTestApp(
        engine=engine,
        market_data=market,
        broker=broker,
        redis_broker=redis_broker,
        runtime_config=runtime,
        engine_id="test",
        max_iterations=len(quotes),
    )
    app.run_forever()

    intents = [i for d in journal.decisions for i in d.order_intents]
    assert any(i.side.value == "BUY" for i in intents)
    assert any(i.side.value == "SELL" for i in intents)
    assert runtime.watchlist_calls >= len(quotes)
    assert runtime.poll_calls >= len(quotes)


def test_override_cli_set_poll_seconds_updates_runtime_config():
    from tests.system.algo_trader.conftest import FakeRuntimeConfig  # local test helper

    runtime = FakeRuntimeConfig(watchlist=["AAPL"], poll_seconds=2.0)
    event = OverrideEvent(
        ts=datetime(2024, 1, 1, tzinfo=timezone.utc),
        command="set_poll_seconds",
        args={"poll_seconds": "1.5"},
    )
    apply_runtime_side_effects("test", event, runtime)
    assert runtime.poll_seconds == 1.5


class _BuyAndHoldStrategy:
    qty: Decimal

    def on_market(self, event: MarketEvent, portfolio) -> list[OrderIntent]:
        _ = event
        if getattr(portfolio, "position", lambda _s: Decimal("0"))("AAPL") > 0:
            return []
        return [OrderIntent(symbol="AAPL", side=Side.BUY, qty=self.qty, reason="test_buy_and_hold")]


def test_portfolio_max_drawdown_emits_flatten_and_pauses(t0, fake_redis_broker, fake_runtime_config):
    sym = "AAPL"

    quotes = [
        {sym: Quote(symbol=sym, ts=t0 + timedelta(seconds=0), price=Decimal("100"))},
        {sym: Quote(symbol=sym, ts=t0 + timedelta(seconds=1), price=Decimal("80"))},
        {sym: Quote(symbol=sym, ts=t0 + timedelta(seconds=2), price=Decimal("80"))},
    ]

    from tests.system.algo_trader.conftest import FakeMarketData, InMemoryJournal, FixedClock

    market = FakeMarketData(quotes_by_call=quotes)
    redis_broker = fake_redis_broker
    broker = PaperBroker()

    clock = FixedClock(now_ts=t0)
    journal = InMemoryJournal()
    portfolio = SimplePortfolio(
        max_drawdown=Decimal("0.10"),
        max_position_fraction=Decimal("1.0"),
        max_gross_exposure_fraction=Decimal("1.0"),
        cooldown_after_drawdown_seconds=60,
    )
    strategy = _BuyAndHoldStrategy(qty=Decimal("1000"))
    engine = Engine(clock=clock, strategy=strategy, portfolio=portfolio, journal=journal)

    runtime = fake_runtime_config
    runtime.watchlist = [sym]
    app = ForwardTestApp(
        engine=engine,
        market_data=market,
        broker=broker,
        redis_broker=redis_broker,
        runtime_config=runtime,
        engine_id="test",
        max_iterations=len(quotes),
    )
    app.run_forever()

    final_intents = [i for d in journal.decisions for i in d.order_intents]
    assert any(i.reason == "risk_max_drawdown_flatten" for i in final_intents)
    assert portfolio.position(sym) == 0
    assert engine.is_paused()


def test_portfolio_resizes_buy_for_max_position_fraction(t0, fake_redis_broker, fake_runtime_config):
    sym = "AAPL"
    quotes = [{sym: Quote(symbol=sym, ts=t0, price=Decimal("100"))}]

    from tests.system.algo_trader.conftest import FakeMarketData, InMemoryJournal, FixedClock

    market = FakeMarketData(quotes_by_call=quotes)
    redis_broker = fake_redis_broker
    broker = PaperBroker()

    clock = FixedClock(now_ts=t0)
    journal = InMemoryJournal()
    portfolio = SimplePortfolio(
        max_drawdown=Decimal("1.0"),
        max_position_fraction=Decimal("0.10"),  # $10k max
        max_gross_exposure_fraction=Decimal("1.0"),
    )
    strategy = _BuyAndHoldStrategy(qty=Decimal("1000"))  # $100k notional at $100
    engine = Engine(clock=clock, strategy=strategy, portfolio=portfolio, journal=journal)

    runtime = fake_runtime_config
    runtime.watchlist = [sym]
    app = ForwardTestApp(
        engine=engine,
        market_data=market,
        broker=broker,
        redis_broker=redis_broker,
        runtime_config=runtime,
        engine_id="test",
        max_iterations=len(quotes),
    )
    app.run_forever()

    assert len(journal.decisions) >= 1
    d0 = journal.decisions[0]
    assert d0.audit is not None
    resized = d0.audit.get("resized", [])
    assert any(r.get("reason") == "max_position_size" for r in resized)
    # 10k / $100 == 100 shares max
    assert all(i.qty <= Decimal("100") for i in d0.order_intents if i.side.value == "BUY")
