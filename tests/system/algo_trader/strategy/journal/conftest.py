"""Shared fixtures for journal tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with patch("infrastructure.logging.logger.get_logger") as mock_logger_func:
        mock_logger_instance = MagicMock()
        mock_logger_func.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_efficiency():
    """Mock calculate_efficiency function."""
    with patch(
        "system.algo_trader.strategy.journal.trade_matching.calculate_efficiency"
    ) as mock_efficiency_func:
        mock_efficiency_func.return_value = 75.0
        yield mock_efficiency_func


@pytest.fixture
def sample_signals_long_entry_exit():
    """Sample signals for LONG entry and exit."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "signal_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-10", tz="UTC"),
            ],
            "signal_type": ["buy", "sell"],
            "price": [100.0, 105.0],
            "side": ["LONG", "LONG"],
        }
    )


@pytest.fixture
def sample_signals_short_entry_exit():
    """Sample signals for SHORT entry and exit."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "signal_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-10", tz="UTC"),
            ],
            "signal_type": ["sell", "buy"],
            "price": [100.0, 95.0],
            "side": ["SHORT", "SHORT"],
        }
    )


@pytest.fixture
def sample_signals_long_entry_only():
    """Sample signals for LONG entry only (no exit)."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "signal_time": [pd.Timestamp("2024-01-05", tz="UTC")],
            "signal_type": ["buy"],
            "price": [100.0],
            "side": ["LONG"],
        }
    )


@pytest.fixture
def sample_signals_long_exit_only():
    """Sample signals for LONG exit only (no entry)."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "signal_time": [pd.Timestamp("2024-01-10", tz="UTC")],
            "signal_type": ["sell"],
            "price": [105.0],
            "side": ["LONG"],
        }
    )


@pytest.fixture
def sample_signals_long_multiple_trades():
    """Sample signals for multiple LONG trades."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "AAPL", "AAPL"],
            "signal_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-10", tz="UTC"),
                pd.Timestamp("2024-01-15", tz="UTC"),
                pd.Timestamp("2024-01-20", tz="UTC"),
            ],
            "signal_type": ["buy", "sell", "buy", "sell"],
            "price": [100.0, 105.0, 110.0, 115.0],
            "side": ["LONG", "LONG", "LONG", "LONG"],
        }
    )


@pytest.fixture
def sample_signals_long_loss():
    """Sample signals for LONG trade with loss."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "signal_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-10", tz="UTC"),
            ],
            "signal_type": ["buy", "sell"],
            "price": [100.0, 95.0],
            "side": ["LONG", "LONG"],
        }
    )


@pytest.fixture
def sample_signals_short_loss():
    """Sample signals for SHORT trade with loss."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "signal_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-10", tz="UTC"),
            ],
            "signal_type": ["sell", "buy"],
            "price": [100.0, 105.0],
            "side": ["SHORT", "SHORT"],
        }
    )


@pytest.fixture
def sample_signals_multiple_tickers():
    """Sample signals for multiple tickers."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT", "MSFT"],
            "signal_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-10", tz="UTC"),
                pd.Timestamp("2024-01-06", tz="UTC"),
                pd.Timestamp("2024-01-11", tz="UTC"),
            ],
            "signal_type": ["buy", "sell", "buy", "sell"],
            "price": [100.0, 105.0, 200.0, 210.0],
            "side": ["LONG", "LONG", "LONG", "LONG"],
        }
    )


@pytest.fixture
def sample_ohlcv_for_efficiency():
    """Sample OHLCV data for efficiency calculation tests."""
    return pd.DataFrame(
        {
            "open": [100.0, 102.0, 104.0, 103.0, 105.0],
            "high": [105.0, 106.0, 107.0, 108.0, 110.0],
            "low": [99.0, 101.0, 103.0, 102.0, 104.0],
            "close": [102.0, 104.0, 106.0, 105.0, 107.0],
        },
        index=pd.date_range("2024-01-05", periods=5, freq="D", tz="UTC"),
    )


@pytest.fixture
def sample_pm_executions_open_close():
    """Sample PM-managed executions: open and close."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL"],
            "signal_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-10", tz="UTC"),
            ],
            "side": ["LONG", "LONG"],
            "price": [100.0, 110.0],
            "shares": [100.0, 100.0],
            "action": ["open", "close"],
            "reason": [None, "strategy_exit"],
        }
    )


@pytest.fixture
def sample_pm_executions_partial_tp():
    """Sample PM-managed executions: open, partial TP, final close."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "AAPL"],
            "signal_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-06", tz="UTC"),
                pd.Timestamp("2024-01-10", tz="UTC"),
            ],
            "side": ["LONG", "LONG", "LONG"],
            "price": [100.0, 101.0, 102.0],
            "shares": [100.0, 50.0, 50.0],
            "action": ["open", "scale_out", "close"],
            "reason": [None, "take_profit", "strategy_exit"],
        }
    )
