"""Shared fixtures for InfluxDB tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

import pytest
import yaml


@pytest.fixture(autouse=True)
def mock_influx_dependencies():
    """Auto-mock all InfluxDB dependencies."""
    with (
        patch("system.algo_trader.influx.market_data_influx.get_logger") as mock_logger,
        patch("infrastructure.influxdb.influxdb.get_logger") as mock_base_logger,
        patch("infrastructure.influxdb.influxdb.InfluxDBClient3") as mock_client_class,
        patch("infrastructure.influxdb.influxdb.write_client_options") as mock_wco,
    ):
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance

        mock_base_logger_instance = MagicMock()
        mock_base_logger.return_value = mock_base_logger_instance

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_wco.return_value = MagicMock()

        yield {
            "logger": mock_logger,
            "logger_instance": mock_logger_instance,
            "base_logger": mock_base_logger,
            "client_class": mock_client_class,
            "client": mock_client,
            "wco": mock_wco,
        }


@pytest.fixture
def mock_queue_broker():
    """Fixture to mock QueueBroker for publisher tests."""
    with patch("system.algo_trader.redis.queue_broker.QueueBroker") as mock_queue_broker_class:
        mock_broker = MagicMock()
        mock_broker.get_queue_size.return_value = 0
        mock_broker.dequeue.return_value = None
        mock_broker.get_data.return_value = None
        mock_broker.delete_data.return_value = True
        mock_broker.peek_queue.return_value = []
        mock_queue_broker_class.return_value = mock_broker
        yield mock_broker


@pytest.fixture
def mock_publisher_logger():
    """Fixture to mock logger for publisher."""
    with patch("system.algo_trader.influx.publisher.publisher.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def mock_market_data_influx():
    """Fixture to mock MarketDataInflux for publisher tests."""
    with patch("system.algo_trader.influx.publisher.config.MarketDataInflux") as mock_client_class:
        mock_client = MagicMock()
        mock_client.write_sync.return_value = True
        mock_client.write.return_value = True  # For queue_processor tests
        mock_client.close.return_value = None
        mock_client_class.return_value = mock_client
        # Yield dict with both class and instance for different test needs
        yield {"class": mock_client_class, "instance": mock_client}


@pytest.fixture
def mock_signal():
    """Fixture to mock signal handling."""
    with patch("system.algo_trader.influx.publisher.publisher.signal.signal") as mock_signal_func:
        yield mock_signal_func


@pytest.fixture
def sample_publisher_config():
    """Sample publisher configuration for testing."""
    return {
        "queues": [
            {
                "name": "ohlcv_queue",
                "table": "ohlcv",
                "namespace": "queue",
                "flush_interval": 5000,
                "jitter_interval": 1000,
                "retry_interval": 10000,
                "max_retries": 3,
                "max_retry_delay": 30000,
                "exponential_base": 2,
                "poll_interval": 2,
            },
            {
                "name": "fundamentals_queue",
                "table": "fundamentals",
                "namespace": "queue",
                "flush_interval": 5000,
                "jitter_interval": 1000,
                "retry_interval": 10000,
                "max_retries": 3,
                "max_retry_delay": 30000,
                "exponential_base": 2,
                "poll_interval": 2,
            },
        ]
    }


@pytest.fixture
def temp_config_file(sample_publisher_config):
    """Create a temporary YAML config file for testing."""
    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(sample_publisher_config, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def mock_check_queues_logger():
    """Fixture to mock logger for check_queues."""
    with patch("system.algo_trader.redis.check_queues.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def mock_check_queues_queue_broker():
    """Fixture to mock QueueBroker for check_queues tests."""
    with patch("system.algo_trader.redis.check_queues.QueueBroker") as mock_queue_broker_class:
        mock_broker = MagicMock()
        mock_broker.get_queue_size.return_value = 0
        mock_broker.peek_queue.return_value = []
        mock_broker.get_data.return_value = None
        mock_queue_broker_class.return_value = mock_broker
        yield mock_broker


@pytest.fixture
def mock_diagnose_mysql():
    """Fixture to mock MySQL dependencies for diagnose_missing_data tests."""
    with patch("infrastructure.mysql.mysql.pymysql") as mock_pymysql_module:
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.return_value = 0
        mock_cursor.rowcount = 0
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = None
        mock_pymysql_module.connect.return_value = mock_connection

        yield {
            "module": mock_pymysql_module,
            "connection": mock_connection,
            "cursor": mock_cursor,
        }


@pytest.fixture
def mock_diagnose_logger():
    """Fixture to mock logger for diagnose_missing_data tests."""
    with patch("infrastructure.logging.logger.get_logger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_diagnose_mysql_config():
    """Fixture to mock MySQLConfig for diagnose_missing_data tests."""
    with patch("infrastructure.config.MySQLConfig") as mock_config_class:
        mock_config = MagicMock()
        mock_config.host = "localhost"
        mock_config.port = 3306
        mock_config.user = "root"
        mock_config.password = ""
        mock_config.database = "algo_trader"
        mock_config.charset = "utf8mb4"
        mock_config.connect_timeout = 10
        mock_config.autocommit = False
        mock_config_class.return_value = mock_config
        yield mock_config


@pytest.fixture
def mock_diagnose_bad_ticker_client():
    """Fixture to mock BadTickerClient for diagnose_missing_data tests."""
    with patch(
        "system.algo_trader.influx.diagnose_missing_data.BadTickerClient"
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client.get_bad_tickers.return_value = []
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_diagnose_tickers():
    """Fixture to mock Tickers class for diagnose_missing_data tests."""
    with patch("system.algo_trader.influx.diagnose_missing_data.Tickers") as mock_tickers_class:
        mock_tickers = MagicMock()
        mock_tickers.get_tickers.return_value = {}
        mock_tickers_class.return_value = mock_tickers
        yield mock_tickers


@pytest.fixture
def mock_diagnose_sp500_tickers():
    """Fixture to mock get_sp500_tickers for diagnose_missing_data tests."""
    with patch("system.algo_trader.influx.diagnose_missing_data.get_sp500_tickers") as mock_sp500:
        mock_sp500.return_value = []
        yield mock_sp500


@pytest.fixture
def sample_candle():
    """Sample candle data structure for queue processor tests."""
    return {
        "datetime": int(time.time() * 1000),
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 104.0,
        "volume": 1000000,
    }


@pytest.fixture
def sample_ohlcv_queue_data(sample_candle):
    """Sample OHLCV queue data structure."""
    return {
        "ticker": "AAPL",
        "candles": [sample_candle],
        "database": "debug",
    }


@pytest.fixture
def sample_backtest_trades_queue_data():
    """Sample backtest trades queue data structure."""
    return {
        "ticker": "AAPL",
        "strategy_name": "SMACrossoverStrategy",
        "backtest_id": "test-id",
        "hash": "abc123",
        "data": {
            "datetime": [1704067200000],
            "entry_price": [100.0],
            "exit_price": [105.0],
            "gross_pnl": [500.0],
        },
        "database": "debug",
    }


@pytest.fixture
def sample_backtest_metrics_queue_data():
    """Sample backtest metrics queue data structure."""
    return {
        "ticker": "AAPL",
        "strategy_name": "SMACrossoverStrategy",
        "backtest_id": "test-id",
        "hash_id": "abc123",
        "data": {
            "datetime": [1704067200000],
            "total_trades": [10],
            "total_profit": [5000.0],
        },
        "database": "debug",
    }
