"""Main CLI entry point for algo_trader.

Supports backtest, forwardtest, and live execution modes based on environment
configuration.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from infrastructure.postgres.postgres import BasePostgresClient
from system.algo_trader.adapters.paper.broker import PaperBroker
from system.algo_trader.adapters.redis.engine_registry import AlgoTraderEngineRegistry
from system.algo_trader.adapters.redis.event_bus import AlgoTraderRedisBroker
from system.algo_trader.adapters.redis.runtime_config import AlgoTraderRuntimeConfigStore
from system.algo_trader.adapters.schwab.market_data import SchwabMarketDataAdapter
from system.algo_trader.adapters.timescale.journal import TimescaleJournal
from system.algo_trader.adapters.timescale.store import AlgoTraderStore
from system.algo_trader.apps.backtest_app import BacktestApp
from system.algo_trader.apps.forward_app import ForwardTestApp
from system.algo_trader.domain.engine import Engine
from system.algo_trader.domain.events import OverrideEvent
from system.algo_trader.domain.portfolio import SimplePortfolio
from system.algo_trader.domain.strategies import SmaCrossoverStrategy
from system.algo_trader.schwab.market_handler import MarketHandler


@dataclass(slots=True)
class RealClock:
    """Real-time clock implementation."""

    def now(self) -> datetime:
        """Get current UTC datetime."""
        return datetime.now(tz=timezone.utc)


def _normalize_mode(raw: str) -> str:
    v = raw.strip().lower()
    if v == "forward":
        return "forwardtest"
    if v == "forward_test":
        return "forwardtest"
    if v == "forward-test":
        return "forwardtest"
    return v


def main() -> None:
    """Main CLI entry point for algo_trader."""
    mode = _normalize_mode(os.getenv("EXECUTION_ENVIRONMENT", "backtest"))
    if mode not in {"backtest", "forwardtest", "live"}:
        raise ValueError("EXECUTION_ENVIRONMENT must be one of: backtest, forwardtest, live")
    if mode == "live":
        raise NotImplementedError("live mode is not implemented yet")

    # Engine identity (used for per-engine Redis keys and Timescale schema).
    engine_id = uuid.uuid4().hex[:12]

    runtime = AlgoTraderRuntimeConfigStore()
    registry = AlgoTraderEngineRegistry()
    registry.register(engine_id, status={"mode": mode, "state": "starting"}, ttl_seconds=15)

    # Defaults so the engine can boot even before an operator sets config.
    if not runtime.get_watchlist(engine_id, limit=1):
        runtime.set_watchlist(engine_id, ["AAPL"])
    if runtime.get(f"{engine_id}:poll_seconds") is None:
        runtime.set_poll_seconds(engine_id, 2.0)

    symbols = runtime.get_watchlist(engine_id, limit=200)

    # Strategy params are app logic (not Redis config for now).
    strategy = SmaCrossoverStrategy(window_a=20, window_b=10)
    portfolio = SimplePortfolio(max_symbols=200)

    db = BasePostgresClient()
    schema = AlgoTraderStore.schema_for_engine(engine_id)
    store = AlgoTraderStore(db=db, schema=schema)
    store.migrate()

    run_id = str(uuid.uuid4())
    store.create_run(
        run_id=run_id,
        mode=mode,
        config={
            "engine_id": engine_id,
            "symbols": symbols,
            "sma": "20/10",
        },
    )

    journal = TimescaleJournal(store=store, run_id=run_id)
    engine = Engine(clock=RealClock(), strategy=strategy, portfolio=portfolio, journal=journal)

    if mode == "backtest":
        start = date.fromisoformat("2020-01-01")
        end = date.today()

        bars = store.get_daily_bars(symbols=symbols, start=start, end=end)
        if not bars:
            # Populate from Schwab once (cached for future backtests).
            market = SchwabMarketDataAdapter(client=MarketHandler())
            bars = list(market.get_daily_bars(symbols=symbols, start=start, end=end))
            store.upsert_daily_bars(bars)

        app = BacktestApp(engine=engine, broker=PaperBroker(), bars=list(bars))
        app.run()
        return

    redis_broker = AlgoTraderRedisBroker(engine_id=engine_id)

    # Record a synthetic "resume" so the run has a start marker in the journal.
    engine.on_override(OverrideEvent(ts=datetime.now(tz=timezone.utc), command="resume", args={}))

    app = ForwardTestApp(
        engine=engine,
        market_data=SchwabMarketDataAdapter(client=MarketHandler()),
        broker=PaperBroker(),
        redis_broker=redis_broker,
        runtime_config=runtime,
        engine_id=engine_id,
        engine_registry=registry,
        max_iterations=None,
    )
    app.run_forever()


if __name__ == "__main__":
    main()
