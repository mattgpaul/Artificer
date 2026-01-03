"""Shared fixtures for backtest tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from datetime import timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.strategy.position_manager.position_manager import PositionManager
from system.algo_trader.strategy.position_manager.rules.pipeline import PositionRulePipeline
from system.algo_trader.strategy.position_manager.rules.scaling import ScalingRule


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with patch("infrastructure.logging.logger.get_logger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
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
    """Mock Strategy for testing."""
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
    with patch("system.algo_trader.backtest.results.writer.QueueBroker") as mock_broker_class:
        mock_broker = MagicMock()
        mock_broker.enqueue.return_value = True
        mock_broker_class.return_value = mock_broker
        yield mock_broker


@pytest.fixture
def mock_process_manager():
    """Mock ProcessManager for BacktestProcessor tests."""
    with patch(
        "system.algo_trader.backtest.processor.parallel.ProcessManager"
    ) as mock_manager_class:
        mock_manager = MagicMock()
        mock_manager.map.return_value = [{"success": True, "trades": 10}]
        mock_manager.close_pool.return_value = None
        mock_manager_class.return_value = mock_manager
        yield mock_manager


@pytest.fixture
def sample_ohlcv_data_with_time(sample_ohlcv_data):
    """Sample OHLCV data with time column (for InfluxDB query format)."""
    data = sample_ohlcv_data.reset_index()
    data = data.rename(columns={"index": "time"})
    return data


@pytest.fixture
def sample_mock_trades():
    """Sample mock trades DataFrame with all required columns for ExecutionSimulator."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
            "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
            "entry_price": [100.0],
            "exit_price": [105.0],
            "shares": [100.0],  # Required by ExecutionSimulator
            "side": ["LONG"],
            "gross_pnl": [500.0],
        }
    )


@pytest.fixture
def sample_mock_signals():
    """Sample mock signals DataFrame for testing."""
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
def sample_mock_signals_single():
    """Sample single signal DataFrame for testing."""
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
def sample_mock_signals_multiple_tickers():
    """Sample signals DataFrame for multiple tickers."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "signal_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-06", tz="UTC"),
            ],
            "signal_type": ["buy", "buy"],
            "price": [100.0, 200.0],
            "side": ["LONG", "LONG"],
        }
    )


@pytest.fixture
def position_manager_config():
    """Create PositionManagerConfig for testing."""
    scaling = ScalingRule(allow_scale_in=False, allow_scale_out=True)
    return PositionRulePipeline([scaling])


@pytest.fixture
def position_manager(position_manager_config):
    """Create PositionManager instance for testing."""
    return PositionManager(position_manager_config)


@pytest.fixture
def sample_mock_signals_with_multiple_entries():
    """Sample signals DataFrame with multiple entry attempts (for position_manager filtering)."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "AAPL", "AAPL"],
            "signal_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-06", tz="UTC"),
                pd.Timestamp("2024-01-07", tz="UTC"),
                pd.Timestamp("2024-01-10", tz="UTC"),
            ],
            "signal_type": ["buy", "buy", "buy", "sell"],
            "price": [100.0, 101.0, 102.0, 105.0],
            "side": ["LONG", "LONG", "LONG", "LONG"],
        }
    )


# Fixtures for cli_utils tests
@pytest.fixture
def mock_influx_client():
    """Fixture to mock MarketDataInflux client for cli_utils tests."""
    with patch("system.algo_trader.backtest.cli_utils.MarketDataInflux") as mock_influx_class:
        mock_client = MagicMock()
        mock_influx_class.return_value = mock_client
        yield {"class": mock_influx_class, "instance": mock_client}


@pytest.fixture
def mock_tickers_class():
    """Fixture to mock SEC Tickers class for cli_utils tests."""
    with patch("system.algo_trader.backtest.cli_utils.Tickers") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield {"class": mock_class, "instance": mock_instance}


@pytest.fixture
def mock_get_sp500():
    """Fixture to mock get_sp500_tickers function for cli_utils tests."""
    with patch("system.algo_trader.backtest.cli_utils.get_sp500_tickers") as mock_func:
        yield mock_func


@pytest.fixture
def sample_signals():
    """Sample signals DataFrame for cli_utils formatting tests."""
    dates = pd.date_range("2024-01-01", periods=5, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "MSFT", "MSFT", "GOOGL"],
            "signal_type": ["buy", "sell", "buy", "sell", "buy"],
            "price": [150.0, 155.0, 350.0, 360.0, 2800.0],
            "confidence": [0.85, 0.90, 0.75, 0.80, 0.70],
            "signal_time": dates,
        },
        index=dates,
    )


@pytest.fixture
def sample_trades_cli():
    """Sample trades DataFrame for cli_utils formatting tests."""
    return pd.DataFrame(
        {
            "entry_time": [
                pd.Timestamp("2024-01-01 10:00:00", tz=timezone.utc),
                pd.Timestamp("2024-01-05 11:00:00", tz=timezone.utc),
                pd.Timestamp("2024-01-10 09:30:00", tz=timezone.utc),
            ],
            "exit_time": [
                pd.Timestamp("2024-01-03 15:00:00", tz=timezone.utc),
                pd.Timestamp("2024-01-08 14:00:00", tz=timezone.utc),
                pd.Timestamp("2024-01-15 16:00:00", tz=timezone.utc),
            ],
            "entry_price": [150.0, 155.0, 148.0],
            "exit_price": [155.0, 152.0, 160.0],
            "shares": [100.0, 100.0, 100.0],
            "gross_pnl": [500.0, -300.0, 800.0],
            "gross_pnl_pct": [3.33, -1.94, 8.11],
        }
    )


@pytest.fixture
def sample_trade_single():
    """Sample single trade DataFrame for ResultsWriter tests."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
            "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
            "entry_price": [100.0],
            "exit_price": [105.0],
            "shares": [100.0],
            "gross_pnl": [500.0],
        }
    )


@pytest.fixture
def sample_trades_multiple():
    """Sample multiple trades DataFrame for ResultsWriter tests."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "entry_time": [
                pd.Timestamp("2024-01-05", tz="UTC"),
                pd.Timestamp("2024-01-06", tz="UTC"),
            ],
            "exit_time": [
                pd.Timestamp("2024-01-10", tz="UTC"),
                pd.Timestamp("2024-01-11", tz="UTC"),
            ],
            "entry_price": [100.0, 200.0],
            "exit_price": [105.0, 210.0],
            "shares": [100.0, 100.0],
            "gross_pnl": [500.0, 1000.0],
        }
    )


@pytest.fixture
def sample_trade_with_nan():
    """Sample trade DataFrame with NaN values for testing NaN handling."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "entry_time": [pd.Timestamp("2024-01-05", tz="UTC")],
            "exit_time": [pd.Timestamp("2024-01-10", tz="UTC")],
            "entry_price": [100.0],
            "exit_price": [105.0],
            "shares": [100.0],
            "gross_pnl": [500.0],
            "optional_field": [None],
        }
    )


@pytest.fixture
def sample_pm_executions_open_tp_close():
    """Sample PM-managed execution intents: open, partial TP, final close."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "AAPL"],
            "signal_time": [
                pd.Timestamp("2024-05-05", tz="UTC"),
                pd.Timestamp("2024-05-06", tz="UTC"),
                pd.Timestamp("2024-05-11", tz="UTC"),
            ],
            "side": ["LONG", "LONG", "LONG"],
            "price": [100.0, 101.0, 102.0],
            "shares": [134.0, 67.0, 67.0],
            "action": ["open", "scale_out", "close"],
            "reason": [None, "take_profit", "strategy_exit"],
        }
    )
