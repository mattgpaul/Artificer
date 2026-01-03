"""Shared fixtures for position_manager tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from datetime import timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.strategy.position_manager.rules.pipeline import PositionRulePipeline
from system.algo_trader.strategy.position_manager.rules.scaling import ScalingRule
from system.algo_trader.strategy.position_manager.rules.stop_loss import StopLossRule
from system.algo_trader.strategy.position_manager.rules.take_profit import TakeProfitRule


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with patch("infrastructure.logging.logger.get_logger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def simple_tp_sl_pipeline():
    """Create a simple PositionRulePipeline with TP and SL rules."""
    scaling = ScalingRule(allow_scale_in=False, allow_scale_out=True)
    take_profit = TakeProfitRule(
        field_price="price", target_pct=0.01, fraction=0.5, anchor_config=None
    )
    stop_loss = StopLossRule(field_price="price", loss_pct=0.2, fraction=1.0, anchor_config=None)
    return PositionRulePipeline([scaling, take_profit, stop_loss])


@pytest.fixture
def sample_signals_long_entry_exit():
    """Sample signals DataFrame with LONG entry and exit."""
    dates = pd.date_range("2024-01-01", periods=4, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT", "MSFT"],
            "signal_type": ["buy", "sell", "buy", "sell"],
            "signal_time": dates,
            "price": [150.0, 155.0, 350.0, 360.0],
            "side": ["LONG", "LONG", "LONG", "LONG"],
        },
        index=dates,
    )


@pytest.fixture
def sample_signals_short_entry_exit():
    """Sample signals DataFrame with SHORT entry and exit."""
    dates = pd.date_range("2024-01-01", periods=4, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT", "MSFT"],
            "signal_type": ["sell", "buy", "sell", "buy"],
            "signal_time": dates,
            "price": [150.0, 145.0, 350.0, 340.0],
            "side": ["SHORT", "SHORT", "SHORT", "SHORT"],
        },
        index=dates,
    )


@pytest.fixture
def sample_signals_multiple_entries():
    """Sample signals DataFrame with multiple entry attempts (should be filtered)."""
    dates = pd.date_range("2024-01-01", periods=5, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "AAPL", "AAPL", "AAPL"],
            "signal_type": ["buy", "buy", "buy", "sell", "buy"],
            "signal_time": dates,
            "price": [150.0, 151.0, 152.0, 155.0, 156.0],
            "side": ["LONG", "LONG", "LONG", "LONG", "LONG"],
        },
        index=dates,
    )


@pytest.fixture
def sample_signals_exit_without_entry():
    """Sample signals DataFrame with exit signal before entry (should be filtered)."""
    dates = pd.date_range("2024-01-01", periods=3, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "AAPL"],
            "signal_type": ["sell", "buy", "sell"],
            "signal_time": dates,
            "price": [150.0, 151.0, 155.0],
            "side": ["LONG", "LONG", "LONG"],
        },
        index=dates,
    )


@pytest.fixture
def sample_signals_no_time_column():
    """Sample signals DataFrame without signal_time column."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "signal_type": ["buy", "sell"],
            "price": [150.0, 155.0],
            "side": ["LONG", "LONG"],
        },
        index=[0, 1],
    )


@pytest.fixture
def sample_ohlcv_by_ticker():
    """Sample OHLCV data by ticker."""
    dates = pd.date_range("2024-01-01", periods=10, freq="1D", tz=timezone.utc)
    return {
        "AAPL": pd.DataFrame(
            {
                "open": [150.0] * 10,
                "high": [155.0] * 10,
                "low": [145.0] * 10,
                "close": [152.0] * 10,
                "volume": [1000000] * 10,
            },
            index=dates,
        ),
        "MSFT": pd.DataFrame(
            {
                "open": [350.0] * 10,
                "high": [360.0] * 10,
                "low": [340.0] * 10,
                "close": [355.0] * 10,
                "volume": [2000000] * 10,
            },
            index=dates,
        ),
    }


@pytest.fixture
def sample_ohlcv_3_bars():
    """Sample OHLCV data for 3 bars (for TP/SL testing)."""
    dates = pd.date_range("2024-01-01", periods=3, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.0, 101.1, 102.0],
            "volume": [1_000_000] * 3,
        },
        index=dates,
    )


@pytest.fixture
def sample_ohlcv_4_bars():
    """Sample OHLCV data for 4 bars (for TP/SL testing with price progression)."""
    dates = pd.date_range("2024-01-01", periods=4, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 103.0],
            "high": [101.0, 102.0, 103.0, 104.0],
            "low": [99.0, 100.0, 101.0, 102.0],
            "close": [100.0, 101.1, 102.0, 103.0],
            "volume": [1_000_000] * 4,
        },
        index=dates,
    )


@pytest.fixture
def sample_signals_entry_only():
    """Sample signals DataFrame with entry only (for PM-generated exit testing)."""
    dates = pd.date_range("2024-01-01", periods=1, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "signal_time": dates,
            "signal_type": ["buy"],
            "price": [100.0],
            "side": ["LONG"],
        }
    )
