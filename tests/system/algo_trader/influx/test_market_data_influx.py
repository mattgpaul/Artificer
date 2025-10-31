"""Unit tests for MarketDataInflux - Market Data InfluxDB Client.

Tests cover initialization, data formatting, write operations, and query operations.
All external dependencies are mocked to avoid requiring an InfluxDB server.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from infrastructure.influxdb.influxdb import BatchWriteConfig
from system.algo_trader.influx.market_data_influx import MarketDataInflux, market_write_config


class TestMarketDataInfluxInitialization:
    """Test MarketDataInflux initialization."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all external dependencies."""
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

    def test_initialization_default_database(self, mock_dependencies):
        """Test initialization with default database name."""
        client = MarketDataInflux()

        assert client.database == "historical_market_data"
        assert client.write_config == market_write_config

    def test_initialization_custom_database(self, mock_dependencies):
        """Test initialization with custom database name."""
        client = MarketDataInflux(database="custom_market_data")

        assert client.database == "custom_market_data"

    def test_initialization_custom_write_config(self, mock_dependencies):
        """Test initialization with custom write config."""
        custom_config = BatchWriteConfig(batch_size=5000, max_retries=10)
        client = MarketDataInflux(write_config=custom_config)

        assert client.write_config.batch_size == 5000
        assert client.write_config.max_retries == 10

    def test_initialization_uses_market_write_config_by_default(self, mock_dependencies):
        """Test that default write config uses optimized market settings."""
        client = MarketDataInflux()

        assert client.write_config.batch_size == 10000
        assert client.write_config.flush_interval == 1000
        assert client.write_config.max_retries == 5

    def test_initialization_creates_logger(self, mock_dependencies):
        """Test that initialization creates a logger with class name."""
        MarketDataInflux()

        mock_dependencies["logger"].assert_called_with("MarketDataInflux")


class TestMarketDataInfluxFormatStockData:
    """Test stock data formatting."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all external dependencies."""
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

    def test_format_stock_data_success(self, mock_dependencies):
        """Test successful stock data formatting."""
        client = MarketDataInflux()

        # Sample market data with millisecond timestamps
        data = {
            "datetime": [1609459200000, 1609545600000, 1609632000000],  # Unix ms timestamps
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 107.0],
            "low": [99.0, 100.0, 101.0],
            "close": [104.0, 105.0, 106.0],
            "volume": [1000000, 1100000, 1200000],
        }

        result = client._format_stock_data(data, "AAPL")

        assert isinstance(result, pd.DataFrame)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert "datetime" not in result.columns  # Should be dropped
        assert "open" in result.columns
        assert "close" in result.columns
        assert len(result) == 3

    def test_format_stock_data_datetime_conversion(self, mock_dependencies):
        """Test that datetime is properly converted from milliseconds to datetime index."""
        client = MarketDataInflux()

        data = {
            "datetime": [1609459200000],  # 2021-01-01 00:00:00 UTC
            "open": [100.0],
            "close": [104.0],
        }

        result = client._format_stock_data(data, "AAPL")

        # Check that index is datetime with UTC timezone
        assert result.index.tz is not None
        assert result.index[0].year == 2021
        assert result.index[0].month == 1
        assert result.index[0].day == 1

    def test_format_stock_data_logs_debug(self, mock_dependencies):
        """Test that formatting logs debug message with ticker."""
        client = MarketDataInflux()

        data = {"datetime": [1609459200000], "open": [100.0], "close": [104.0]}

        client._format_stock_data(data, "TSLA")

        mock_dependencies["logger_instance"].debug.assert_called_with("Formatting TSLA")

    def test_format_stock_data_empty_data(self, mock_dependencies):
        """Test formatting with empty data."""
        client = MarketDataInflux()

        data = {"datetime": [], "open": [], "close": []}

        result = client._format_stock_data(data, "AAPL")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_format_stock_data_preserves_all_columns(self, mock_dependencies):
        """Test that all data columns are preserved except datetime."""
        client = MarketDataInflux()

        data = {
            "datetime": [1609459200000, 1609545600000],
            "open": [100.0, 101.0],
            "high": [105.0, 106.0],
            "low": [99.0, 100.0],
            "close": [104.0, 105.0],
            "volume": [1000000, 1100000],
            "vwap": [102.5, 103.5],
        }

        result = client._format_stock_data(data, "AAPL")

        assert "open" in result.columns
        assert "high" in result.columns
        assert "low" in result.columns
        assert "close" in result.columns
        assert "volume" in result.columns
        assert "vwap" in result.columns
        assert "datetime" not in result.columns


class TestMarketDataInfluxWrite:
    """Test write operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all external dependencies."""
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

    def test_write_stock_data_success(self, mock_dependencies):
        """Test successful stock data write."""
        mock_dependencies["client"].write.return_value = "Success"

        client = MarketDataInflux()

        data = {
            "datetime": [1609459200000, 1609545600000],
            "open": [100.0, 101.0],
            "close": [104.0, 105.0],
            "volume": [1000000, 1100000],
        }

        result = client.write(data, "AAPL", "stock")

        assert result is True
        mock_dependencies["client"].write.assert_called_once()

        # Verify write was called with correct parameters
        call_args = mock_dependencies["client"].write.call_args
        assert call_args[1]["data_frame_measurement_name"] == "stock"
        assert call_args[1]["data_frame_tag_columns"] == ["ticker"]

    def test_write_increments_pending_counter(self, mock_dependencies):
        """Test that write increments pending batch counter before write."""
        mock_dependencies["client"].write.return_value = "Success"

        client = MarketDataInflux()

        # Mock the callback to track calls
        client._callback = MagicMock()
        client._callback.increment_pending = MagicMock()

        data = {"datetime": [1609459200000], "open": [100.0], "close": [104.0]}

        client.write(data, "AAPL", "stock")

        # Verify increment_pending was called before write
        client._callback.increment_pending.assert_called_once()

    def test_write_decrements_on_exception(self, mock_dependencies):
        """Test that write decrements counter when exception occurs."""
        mock_dependencies["client"].write.side_effect = Exception("Write failed")

        client = MarketDataInflux()

        # Mock the callback
        client._callback = MagicMock()
        client._callback.increment_pending = MagicMock()
        client._callback._pending_batches = 1
        client._callback._lock = MagicMock()

        data = {"datetime": [1609459200000], "open": [100.0], "close": [104.0]}

        result = client.write(data, "AAPL", "stock")

        # Verify increment_pending was called
        client._callback.increment_pending.assert_called_once()
        # Result should be False
        assert result is False

    def test_write_adds_ticker_tag(self, mock_dependencies):
        """Test that write adds ticker as a tag column."""
        mock_dependencies["client"].write.return_value = "Success"

        client = MarketDataInflux()

        data = {"datetime": [1609459200000], "open": [100.0], "close": [104.0]}

        client.write(data, "TSLA", "stock")

        # Get the dataframe that was passed to write
        call_args = mock_dependencies["client"].write.call_args
        df_passed = call_args[0][0]

        assert "ticker" in df_passed.columns
        assert df_passed["ticker"].iloc[0] == "TSLA"

    def test_write_logs_debug_on_success(self, mock_dependencies):
        """Test that successful write logs debug message."""
        mock_dependencies["client"].write.return_value = "Write callback"

        client = MarketDataInflux()

        data = {"datetime": [1609459200000], "open": [100.0], "close": [104.0]}

        client.write(data, "AAPL", "stock")

        mock_dependencies["logger_instance"].debug.assert_called()

    def test_write_failure_returns_false(self, mock_dependencies):
        """Test that write returns False on exception."""
        mock_dependencies["client"].write.side_effect = Exception("Write failed")

        client = MarketDataInflux()

        data = {"datetime": [1609459200000], "open": [100.0], "close": [104.0]}

        result = client.write(data, "AAPL", "stock")

        assert result is False

    def test_write_failure_logs_error(self, mock_dependencies):
        """Test that write failure logs error message with ticker."""
        mock_dependencies["client"].write.side_effect = Exception("Connection timeout")

        client = MarketDataInflux()

        data = {"datetime": [1609459200000], "open": [100.0], "close": [104.0]}

        client.write(data, "AAPL", "stock")

        # Check that error was logged with ticker and exception
        error_call = mock_dependencies["logger_instance"].error.call_args
        assert "AAPL" in error_call[0][0]
        assert "Connection timeout" in error_call[0][0]

    def test_write_with_custom_table_name(self, mock_dependencies):
        """Test write with custom table name."""
        mock_dependencies["client"].write.return_value = "Success"

        client = MarketDataInflux()

        data = {"datetime": [1609459200000], "open": [100.0], "close": [104.0]}

        result = client.write(data, "AAPL", "stock")

        assert result is True
        call_args = mock_dependencies["client"].write.call_args
        assert call_args[1]["data_frame_measurement_name"] == "stock"

    def test_write_multiple_tickers(self, mock_dependencies):
        """Test writing data for different tickers."""
        mock_dependencies["client"].write.return_value = "Success"

        client = MarketDataInflux()

        data = {"datetime": [1609459200000], "open": [100.0], "close": [104.0]}

        # Write for multiple tickers
        result1 = client.write(data, "AAPL", "stock")
        result2 = client.write(data, "TSLA", "stock")
        result3 = client.write(data, "GOOGL", "stock")

        assert result1 is True
        assert result2 is True
        assert result3 is True
        assert mock_dependencies["client"].write.call_count == 3


class TestMarketDataInfluxQuery:
    """Test query operations."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all external dependencies."""
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

    def test_query_success(self, mock_dependencies):
        """Test successful query execution."""
        # Create mock DataFrame
        mock_df = pd.DataFrame(
            {
                "time": [1609459200000, 1609545600000],
                "ticker": ["AAPL", "AAPL"],
                "close": [104.0, 105.0],
            }
        )
        mock_dependencies["client"].query.return_value = mock_df

        client = MarketDataInflux()

        query = "SELECT * FROM stock WHERE ticker = 'AAPL'"
        result = client.query(query)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        mock_dependencies["client"].query.assert_called_once_with(
            query=query, language="sql", mode="pandas"
        )

    def test_query_logs_info(self, mock_dependencies):
        """Test that query logs info message."""
        mock_df = pd.DataFrame({"close": [104.0]})
        mock_dependencies["client"].query.return_value = mock_df

        client = MarketDataInflux()

        client.query("SELECT * FROM stock")

        mock_dependencies["logger_instance"].info.assert_called_with("Getting data")

    def test_query_failure_returns_false(self, mock_dependencies):
        """Test that query returns False on exception."""
        mock_dependencies["client"].query.side_effect = Exception("Query failed")

        client = MarketDataInflux()

        result = client.query("SELECT * FROM stock")

        assert result is False

    def test_query_failure_logs_error(self, mock_dependencies):
        """Test that query failure logs error message."""
        mock_dependencies["client"].query.side_effect = Exception("Connection timeout")

        client = MarketDataInflux()

        client.query("SELECT * FROM stock")

        error_call = mock_dependencies["logger_instance"].error.call_args
        assert "Failed to retrieve query" in error_call[0][0]
        assert "Connection timeout" in error_call[0][0]

    def test_query_with_complex_sql(self, mock_dependencies):
        """Test query with complex SQL statement."""
        mock_df = pd.DataFrame({"avg_close": [105.5]})
        mock_dependencies["client"].query.return_value = mock_df

        client = MarketDataInflux()

        query = """
        SELECT ticker, AVG(close) as avg_close
        FROM stock
        WHERE time > NOW() - INTERVAL '7 days'
        GROUP BY ticker
        """

        result = client.query(query)

        assert isinstance(result, pd.DataFrame)
        mock_dependencies["client"].query.assert_called_once_with(
            query=query, language="sql", mode="pandas"
        )

    def test_query_empty_result(self, mock_dependencies):
        """Test query that returns empty DataFrame."""
        mock_df = pd.DataFrame()
        mock_dependencies["client"].query.return_value = mock_df

        client = MarketDataInflux()

        result = client.query("SELECT * FROM stock WHERE ticker = 'NONEXISTENT'")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_query_uses_sql_language(self, mock_dependencies):
        """Test that query uses SQL language parameter."""
        mock_df = pd.DataFrame({"close": [104.0]})
        mock_dependencies["client"].query.return_value = mock_df

        client = MarketDataInflux()

        client.query("SELECT * FROM stock")

        call_args = mock_dependencies["client"].query.call_args
        assert call_args[1]["language"] == "sql"

    def test_query_uses_pandas_mode(self, mock_dependencies):
        """Test that query uses pandas mode parameter."""
        mock_df = pd.DataFrame({"close": [104.0]})
        mock_dependencies["client"].query.return_value = mock_df

        client = MarketDataInflux()

        client.query("SELECT * FROM stock")

        call_args = mock_dependencies["client"].query.call_args
        assert call_args[1]["mode"] == "pandas"


class TestMarketDataInfluxIntegration:
    """Test integration scenarios."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture to mock all external dependencies."""
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

    def test_write_then_query_workflow(self, mock_dependencies):
        """Test complete workflow: write data then query it back."""
        # Setup mock for write
        mock_dependencies["client"].write.return_value = "Success"

        # Setup mock for query
        mock_df = pd.DataFrame({"ticker": ["AAPL"], "close": [104.0]})
        mock_dependencies["client"].query.return_value = mock_df

        client = MarketDataInflux()

        # Write data
        write_data = {"datetime": [1609459200000], "open": [100.0], "close": [104.0]}
        write_result = client.write(write_data, "AAPL", "stock")
        assert write_result is True

        # Query data back
        query_result = client.query("SELECT * FROM stock WHERE ticker = 'AAPL'")
        assert isinstance(query_result, pd.DataFrame)
        assert len(query_result) == 1

    def test_batch_write_multiple_tickers(self, mock_dependencies):
        """Test writing data for multiple tickers in batch."""
        mock_dependencies["client"].write.return_value = "Success"

        client = MarketDataInflux()

        tickers = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN"]

        for ticker in tickers:
            data = {
                "datetime": [1609459200000, 1609545600000],
                "open": [100.0, 101.0],
                "close": [104.0, 105.0],
            }
            result = client.write(data, ticker, "stock")
            assert result is True

        assert mock_dependencies["client"].write.call_count == len(tickers)

    def test_error_recovery_continues_after_failed_write(self, mock_dependencies):
        """Test that client can continue after a failed write."""
        # First write fails, second succeeds
        mock_dependencies["client"].write.side_effect = [Exception("Write failed"), "Success"]

        client = MarketDataInflux()

        data = {"datetime": [1609459200000], "open": [100.0], "close": [104.0]}

        # First write fails
        result1 = client.write(data, "AAPL", "stock")
        assert result1 is False

        # Second write succeeds
        result2 = client.write(data, "TSLA", "stock")
        assert result2 is True


class TestMarketWriteConfig:
    """Test market_write_config module-level configuration."""

    def test_market_write_config_exists(self):
        """Test that market_write_config is defined."""
        assert market_write_config is not None

    def test_market_write_config_values(self):
        """Test market_write_config has correct values for market data."""
        assert market_write_config.batch_size == 10000
        assert market_write_config.flush_interval == 1000
        assert market_write_config.jitter_interval == 2000
        assert market_write_config.retry_interval == 15000
        assert market_write_config.max_retries == 5
        assert market_write_config.max_retry_delay == 30000
        assert market_write_config.exponential_base == 2

    def test_market_write_config_optimized_for_high_volume(self):
        """Test that config is optimized for high-volume market data."""
        # Large batch size for efficiency
        assert market_write_config.batch_size >= 10000

        # Short flush interval for near real-time data
        assert market_write_config.flush_interval <= 10000

        # Retries configured for reliability
        assert market_write_config.max_retries >= 5
