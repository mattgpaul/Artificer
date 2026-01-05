from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from infrastructure.postgres.postgres import BasePostgresClient
from system.algo_trader.adapters.paper.broker import PaperBroker
from system.algo_trader.adapters.redis.event_bus import AlgoTraderRedisBroker
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
    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)


def _env_csv(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items


def _env_date(name: str, default: str) -> date:
    raw = os.getenv(name, default)
    return date.fromisoformat(raw)


def _env_sma_windows(default: str = "20/10") -> tuple[int, int]:
    raw = os.getenv("ARTIFICER_ALGO_TRADER_SMA", default).strip()
    if "/" in raw:
        a, b = raw.split("/", 1)
        return int(a), int(b)
    parts = raw.split(",")
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    raise ValueError("ARTIFICER_ALGO_TRADER_SMA must be like '20/10' or '20,10'")


def main() -> None:
    mode = os.getenv("ARTIFICER_ALGO_TRADER_MODE", "backtest").strip().lower()
    if mode not in {"backtest", "forward"}:
        raise ValueError("ARTIFICER_ALGO_TRADER_MODE must be one of: backtest, forward")

    symbols = _env_csv("ARTIFICER_ALGO_TRADER_SYMBOLS", "AAPL")
    if not symbols:
        raise ValueError("ARTIFICER_ALGO_TRADER_SYMBOLS must be a non-empty CSV (e.g., AAPL,MSFT)")

    a, b = _env_sma_windows("20/10")
    strategy = SmaCrossoverStrategy(window_a=a, window_b=b)
    portfolio = SimplePortfolio(max_symbols=200)

    db = BasePostgresClient()
    store = AlgoTraderStore(db=db)
    store.migrate()

    run_id = os.getenv("ARTIFICER_ALGO_TRADER_RUN_ID", "").strip() or str(uuid.uuid4())
    store.create_run(
        run_id=run_id,
        mode=mode,
        config={
            "symbols": symbols,
            "sma": f"{a}/{b}",
        },
    )

    journal = TimescaleJournal(store=store, run_id=run_id)
    engine = Engine(clock=RealClock(), strategy=strategy, portfolio=portfolio, journal=journal)

    if mode == "backtest":
        start = _env_date("ARTIFICER_ALGO_TRADER_START", "2020-01-01")
        end = _env_date("ARTIFICER_ALGO_TRADER_END", date.today().isoformat())

        bars = store.get_daily_bars(symbols=symbols, start=start, end=end)
        if not bars:
            # Populate from Schwab once (cached for future backtests).
            market = SchwabMarketDataAdapter(client=MarketHandler())
            bars = list(market.get_daily_bars(symbols=symbols, start=start, end=end))
            store.upsert_daily_bars(bars)

        app = BacktestApp(engine=engine, broker=PaperBroker(), bars=list(bars))
        app.run()
        return

    redis_broker = AlgoTraderRedisBroker()

    # Record a synthetic "resume" so the run has a start marker in the journal.
    engine.on_override(OverrideEvent(ts=datetime.now(tz=timezone.utc), command="resume", args={}))

    app = ForwardTestApp(
        engine=engine,
        market_data=SchwabMarketDataAdapter(client=MarketHandler()),
        broker=PaperBroker(),
        redis_broker=redis_broker,
        poll_seconds=float(os.getenv("ARTIFICER_ALGO_TRADER_POLL_SECONDS", "2.0")),
        symbols=symbols,
        max_iterations=None,
    )
    app.run_forever()


if __name__ == "__main__":
    main()

