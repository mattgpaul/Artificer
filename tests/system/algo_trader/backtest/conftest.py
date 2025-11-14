"""Shared fixtures for backtest tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.backtest.execution import ExecutionConfig


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with (
        patch("system.algo_trader.backtest.engine.get_logger") as mock_get_logger,
        patch("system.algo_trader.backtest.processor.get_logger") as mock_processor_logger,
        patch("system.algo_trader.backtest.results.get_logger") as mock_results_logger,
    ):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        mock_processor_logger.return_value = mock_logger_instance
        mock_results_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_market_data_influx():
    """Mock MarketDataInflux client."""
    with patch("system.algo_trader.backtest.engine.MarketDataInflux") as mock_client_class:
        mock_client = MagicMock()
        mock_client.query.return_value = None
        mock_client.close.return_value = None
        mock_client_class.return_value = mock_client
        yield {"class": mock_client_class, "instance": mock_client}


@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0 + i * 0.1 for i in range(100)],
            "high": [101.0 + i * 0.1 for i in range(100)],
            "low": [99.0 + i * 0.1 for i in range(100)],
            "close": [100.5 + i * 0.1 for i in range(100)],
            "volume": [1000000] * 100,
        },
        index=dates,
    )


@pytest.fixture
def mock_strategy():
    """Mock BaseStrategy for testing."""
    mock_strategy = MagicMock()
    mock_strategy.strategy_name = "TestStrategy"
    mock_strategy.query_ohlcv = MagicMock(return_value=pd.DataFrame())
    mock_strategy.run_strategy = MagicMock(return_value=pd.DataFrame())
    mock_strategy.close = MagicMock()
    return mock_strategy


@pytest.fixture
def execution_config():
    """Create ExecutionConfig for testing."""
    return ExecutionConfig(
        slippage_bps=5.0,
        commission_per_share=0.005,
        use_limit_orders=False,
        fill_delay_minutes=0,
    )


@pytest.fixture
def sample_trades():
    """Sample trades DataFrame for testing."""
    dates = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "ticker": ["AAPL"] * 5,
            "entry_time": dates,
            "exit_time": dates + pd.Timedelta(days=1),
            "entry_price": [100.0, 101.0, 102.0, 103.0, 104.0],
            "exit_price": [101.0, 102.0, 103.0, 104.0, 105.0],
            "shares": [100] * 5,
            "side": ["LONG"] * 5,
            "gross_pnl": [100.0, 100.0, 100.0, 100.0, 100.0],
            "net_pnl": [99.0, 99.0, 99.0, 99.0, 99.0],
            "commission": [1.0] * 5,
        }
    )


@pytest.fixture
def mock_queue_broker():
    """Mock QueueBroker for ResultsWriter tests."""
    with patch("system.algo_trader.backtest.results.QueueBroker") as mock_broker_class:
        mock_broker = MagicMock()
        mock_broker.enqueue.return_value = True
        mock_broker_class.return_value = mock_broker
        yield mock_broker


@pytest.fixture
def mock_process_manager():
    """Mock ProcessManager for BacktestProcessor tests."""
    with patch("system.algo_trader.backtest.processor.ProcessManager") as mock_manager_class:
        mock_manager = MagicMock()
        mock_manager.map.return_value = [{"success": True, "trades": 10}]
        mock_manager.close_pool.return_value = None
        mock_manager_class.return_value = mock_manager
        yield mock_manager
