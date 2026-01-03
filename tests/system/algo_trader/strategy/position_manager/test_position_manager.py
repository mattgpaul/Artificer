"""Unit and integration tests for PositionManager.

Tests cover:
- PM-managed execution intents (open / scale_out / close with shares & reasons)
- One-shot take-profit behavior (fires once per position)
- Strategy exits closing remaining position after partial TP.

All shared fixtures are defined in conftest.py.
"""

from datetime import timezone

import pandas as pd
import pytest

from system.algo_trader.strategy.position_manager.position_manager import PositionManager


class TestPositionManagerPmManaged:
    """Test PositionManager in PM-managed (bar-driven) mode."""

    @pytest.mark.unit
    def test_apply_generates_open_tp_and_strategy_exit(
        self,
        simple_tp_sl_pipeline,
    ):
        """PM should open, take partial profit once, then close on strategy exit."""
        # Set up OHLCV for a single ticker with:
        # t0: entry at 100
        # t1: +1.1% (TP trigger)
        # t2: arbitrary later bar
        dates = pd.date_range("2020-05-05", periods=3, freq="1D", tz=timezone.utc)
        ohlcv = pd.DataFrame(
            {
                "open": [100.0, 101.0, 102.0],
                "high": [101.0, 102.0, 103.0],
                "low": [99.0, 100.0, 101.0],
                "close": [100.0, 101.1, 102.0],
                "volume": [1_000_000] * 3,
            },
            index=dates,
        )

        # Strategy emits one LONG entry at t0 and one explicit exit at t2.
        signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "signal_time": [dates[0], dates[2]],
                "signal_type": ["buy", "sell"],
                "price": [100.0, 102.0],
                "side": ["LONG", "LONG"],
            }
        )

        pm = PositionManager(simple_tp_sl_pipeline, capital_per_trade=10_000.0)

        result = pm.apply(signals, {"AAPL": ohlcv})
        assert not result.empty

        # Expect three executions:
        # - open ~10000/100 = 100 shares
        # - TP scale_out 0.5 of position
        # - final close of remaining 0.5 on strategy exit
        assert len(result) == 3

        open_row = result.iloc[0]
        tp_row = result.iloc[1]
        final_row = result.iloc[2]

        # Open
        assert open_row["action"] == "open"
        assert open_row["reason"] == "strategy_entry"
        assert open_row["ticker"] == "AAPL"
        assert open_row["signal_time"] == dates[0]
        # Shares opened should be capital_per_trade / entry_price
        assert pytest.approx(open_row["shares"], rel=1e-6) == 10_000.0 / 100.0

        # Take profit (one-shot, 50% of position)
        assert tp_row["action"] == "scale_out"
        assert tp_row["reason"] == "take_profit"
        assert tp_row["signal_time"] == dates[1]
        assert pytest.approx(tp_row["shares"], rel=1e-6) == open_row["shares"] * 0.5

        # Final strategy exit should close the remainder
        assert final_row["action"] == "close"
        assert final_row["reason"] == "strategy_exit"
        assert final_row["signal_time"] == dates[2]
        remaining = open_row["shares"] - tp_row["shares"]
        assert remaining > 0
        assert pytest.approx(final_row["shares"], rel=1e-6) == remaining

    @pytest.mark.unit
    def test_take_profit_one_shot_fires_only_once(self, simple_tp_sl_pipeline):
        """TP rule should not fire more than once for a single position."""
        dates = pd.date_range("2020-05-05", periods=4, freq="1D", tz=timezone.utc)
        # Close stays above +1% after first trigger
        ohlcv = pd.DataFrame(
            {
                "open": [100.0, 101.0, 102.0, 103.0],
                "high": [101.0, 102.0, 103.0, 104.0],
                "low": [99.0, 100.0, 101.0, 102.0],
                "close": [100.0, 101.1, 102.0, 103.0],
                "volume": [1_000_000] * 4,
            },
            index=dates,
        )

        signals = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "signal_time": [dates[0]],
                "signal_type": ["buy"],
                "price": [100.0],
                "side": ["LONG"],
            }
        )

        pm = PositionManager(simple_tp_sl_pipeline, capital_per_trade=10_000.0)
        result = pm.apply(signals, {"AAPL": ohlcv})

        # Expect only one scale_out from TP despite price staying > target
        tp_rows = result[result["reason"] == "take_profit"]
        assert len(tp_rows) == 1
