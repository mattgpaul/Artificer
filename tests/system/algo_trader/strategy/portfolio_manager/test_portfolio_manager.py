import pandas as pd

from system.algo_trader.strategy.portfolio_manager.portfolio_manager import (
    PortfolioManager,
)
from system.algo_trader.strategy.portfolio_manager.rules.base import (
    PortfolioRulePipeline,
)


def _make_ohlcv(days: list[str]) -> dict[str, pd.DataFrame]:
    idx = pd.to_datetime(days, utc=True)
    df = pd.DataFrame(
        {
            "open": [100.0 for _ in days],
            "high": [101.0 for _ in days],
            "low": [99.0 for _ in days],
            "close": [100.0 for _ in days],
            "volume": [1000 for _ in days],
        },
        index=idx,
    )
    return {"TEST": df}


def test_portfolio_manager_keeps_valid_open_and_close():
    executions = pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "strategy": "SMA",
                "side": "LONG",
                "action": "buy_to_open",
                "price": 10.0,
                "shares": 10.0,
                "signal_time": pd.Timestamp("2020-01-01", tz="UTC"),
                "hash": "hash1",
            },
            {
                "ticker": "TEST",
                "strategy": "SMA",
                "side": "LONG",
                "action": "sell_to_close",
                "price": 11.0,
                "shares": 10.0,
                "signal_time": pd.Timestamp("2020-01-02", tz="UTC"),
                "hash": "hash1",
            },
        ]
    )

    ohlcv = _make_ohlcv(["2020-01-01", "2020-01-02", "2020-01-03"])
    pipeline = PortfolioRulePipeline(rules=[])
    pm = PortfolioManager(
        pipeline=pipeline,
        initial_account_value=100000.0,
        settlement_lag_trading_days=2,
    )

    approved = pm.apply(executions, ohlcv)

    assert len(approved) == 2
    assert set(approved["action"]) == {"buy_to_open", "sell_to_close"}


def test_portfolio_manager_drops_close_without_position():
    executions = pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "strategy": "SMA",
                "side": "LONG",
                "action": "buy_to_open",
                "price": 10.0,
                "shares": 1000.0,
                "signal_time": pd.Timestamp("2020-01-01", tz="UTC"),
                "hash": "hash1",
            },
            {
                "ticker": "TEST",
                "strategy": "SMA",
                "side": "LONG",
                "action": "sell_to_close",
                "price": 11.0,
                "shares": 1000.0,
                "signal_time": pd.Timestamp("2020-01-02", tz="UTC"),
                "hash": "hash1",
            },
        ]
    )

    ohlcv = _make_ohlcv(["2020-01-01", "2020-01-02", "2020-01-03"])
    pipeline = PortfolioRulePipeline(rules=[])

    pm = PortfolioManager(
        pipeline=pipeline,
        initial_account_value=50.0,
        settlement_lag_trading_days=2,
    )

    approved = pm.apply(executions, ohlcv)

    assert approved.empty


