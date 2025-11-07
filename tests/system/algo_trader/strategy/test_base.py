"""Unit tests for BaseStrategy - Base class for trading strategies.

Tests cover OHLCV querying, signal writing/reading, single-ticker workflow,
multi-ticker workflow (both sequential and threaded), and error handling.
All external dependencies (InfluxDB, ThreadManager) are mocked.
"""

from datetime import timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from infrastructure.influxdb.influxdb import BatchWriteConfig
from system.algo_trader.strategy.base import BaseStrategy, strategy_write_config


class ConcreteStrategy(BaseStrategy):
    """Concrete implementation for testing BaseStrategy."""

    def __init__(
        self,
        strategy_name: str = "test_strategy",
        database: str = "test-database",
        write_config: BatchWriteConfig = strategy_write_config,
        use_threading: bool = False,
        config=None,
    ):
        """Initialize concrete strategy for testing."""
        super().__init__(strategy_name, database, write_config, use_threading, config)

    def generate_signals(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Mock signal generation that returns simple buy/sell signals."""
        # Return simple signals based on data length
        if len(ohlcv_data) < 2:
            return pd.DataFrame()

        signals = pd.DataFrame(
            {
                "signal_type": ["buy", "sell"],
                "price": [ohlcv_data["close"].iloc[0], ohlcv_data["close"].iloc[-1]],
                "confidence": [0.85, 0.92],
            },
            index=[ohlcv_data.index[0], ohlcv_data.index[-1]],
        )
        return signals


@pytest.fixture
def mock_dependencies():
    """Fixture to mock all external dependencies."""
    with (
        patch("system.algo_trader.strategy.base.get_logger") as mock_logger,
        patch("system.algo_trader.strategy.base.MarketDataInflux") as mock_influx_class,
        patch("system.algo_trader.strategy.base.ThreadManager") as mock_thread_class,
    ):
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance

        mock_influx_instance = MagicMock()
        mock_influx_class.return_value = mock_influx_instance

        mock_thread_instance = MagicMock()
        mock_thread_class.return_value = mock_thread_instance

        yield {
            "logger": mock_logger,
            "logger_instance": mock_logger_instance,
            "influx_class": mock_influx_class,
            "influx_instance": mock_influx_instance,
            "thread_class": mock_thread_class,
            "thread_instance": mock_thread_instance,
        }


@pytest.fixture
def sample_ohlcv_data():
    """Fixture providing sample OHLCV data."""
    dates = pd.date_range("2024-01-01", periods=5, freq="1D", tz=timezone.utc)
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [105.0, 106.0, 107.0, 108.0, 109.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [104.0, 105.0, 106.0, 107.0, 108.0],
            "volume": [1000000, 1100000, 1200000, 1300000, 1400000],
            "ticker": ["AAPL", "AAPL", "AAPL", "AAPL", "AAPL"],
        },
        index=dates,
    )


class TestBaseStrategyInitialization:
    """Test BaseStrategy initialization and configuration."""

    def test_initialization_default_config(self, mock_dependencies):
        """Test initialization with default configuration."""
        strategy = ConcreteStrategy()

        assert strategy.strategy_name == "test_strategy"
        assert strategy.influx_client is not None
        assert strategy.thread_manager is None

        mock_dependencies["influx_class"].assert_called_once_with(
            database="test-database", write_config=strategy_write_config, config=None
        )

    def test_initialization_with_threading(self, mock_dependencies):
        """Test initialization with threading enabled."""
        strategy = ConcreteStrategy(use_threading=True)

        assert strategy.thread_manager is not None
        mock_dependencies["thread_class"].assert_called_once()

    def test_initialization_custom_database(self, mock_dependencies):
        """Test initialization with custom database name."""
        _ = ConcreteStrategy(database="custom-db")

        mock_dependencies["influx_class"].assert_called_once_with(
            database="custom-db", write_config=strategy_write_config, config=None
        )

    def test_initialization_custom_write_config(self, mock_dependencies):
        """Test initialization with custom write configuration."""
        custom_config = BatchWriteConfig(batch_size=100, max_retries=10)
        _ = ConcreteStrategy(write_config=custom_config)

        mock_dependencies["influx_class"].assert_called_once_with(
            database="test-database", write_config=custom_config, config=None
        )


class TestQueryOHLCV:
    """Test OHLCV data querying from InfluxDB."""

    def test_query_ohlcv_success(self, mock_dependencies, sample_ohlcv_data):
        """Test successful OHLCV query with time indexing."""
        mock_dependencies[
            "influx_instance"
        ].query.return_value = sample_ohlcv_data.reset_index().rename(columns={"index": "time"})

        strategy = ConcreteStrategy()
        result = strategy.query_ohlcv("AAPL")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
        assert isinstance(result.index, pd.DatetimeIndex)
        mock_dependencies["influx_instance"].query.assert_called_once()

    def test_query_ohlcv_with_filters(self, mock_dependencies, sample_ohlcv_data):
        """Test OHLCV query with start/end time filters."""
        mock_dependencies[
            "influx_instance"
        ].query.return_value = sample_ohlcv_data.reset_index().rename(columns={"index": "time"})

        strategy = ConcreteStrategy()
        strategy.query_ohlcv("AAPL", start_time="2024-01-01", end_time="2024-01-31", limit=100)

        call_args = mock_dependencies["influx_instance"].query.call_args
        query = call_args[0][0]
        assert "ticker = 'AAPL'" in query
        assert "time >= '2024-01-01'" in query
        assert "time <= '2024-01-31'" in query
        assert "LIMIT 100" in query

    def test_query_ohlcv_no_data(self, mock_dependencies):
        """Test OHLCV query when no data is returned."""
        mock_dependencies["influx_instance"].query.return_value = None

        strategy = ConcreteStrategy()
        result = strategy.query_ohlcv("NONEXISTENT")

        assert result is None

    def test_query_ohlcv_empty_dataframe(self, mock_dependencies):
        """Test OHLCV query when empty DataFrame is returned."""
        mock_dependencies["influx_instance"].query.return_value = False

        strategy = ConcreteStrategy()
        result = strategy.query_ohlcv("AAPL")

        assert result is None

    def test_query_ohlcv_exception(self, mock_dependencies):
        """Test OHLCV query when exception occurs."""
        mock_dependencies["influx_instance"].query.side_effect = Exception("Query failed")

        strategy = ConcreteStrategy()
        result = strategy.query_ohlcv("AAPL")

        assert result is None


class TestWriteSignals:
    """Test signal writing to InfluxDB."""

    def test_write_signals_success(self, mock_dependencies):
        """Test successful signal writing with required columns."""
        mock_dependencies["influx_instance"].write.return_value = True

        strategy = ConcreteStrategy()
        signals = pd.DataFrame(
            {"signal_type": ["buy", "sell"], "price": [100.0, 105.0], "confidence": [0.8, 0.9]},
            index=pd.DatetimeIndex(["2024-01-01", "2024-01-02"], tz=timezone.utc),
        )

        result = strategy.write_signals(signals, "AAPL")

        assert result is True
        mock_dependencies["influx_instance"].write.assert_called_once()

        # Verify write was called with correct parameters
        call_args = mock_dependencies["influx_instance"].write.call_args
        assert call_args[1]["ticker"] == "AAPL"
        assert call_args[1]["table"] == "strategy"

    def test_write_signals_empty_dataframe(self, mock_dependencies):
        """Test writing empty signals DataFrame."""
        strategy = ConcreteStrategy()
        signals = pd.DataFrame()

        result = strategy.write_signals(signals, "AAPL")

        assert result is True
        mock_dependencies["influx_instance"].write.assert_not_called()

    def test_write_signals_missing_columns(self, mock_dependencies):
        """Test writing signals with missing required columns."""
        strategy = ConcreteStrategy()
        signals = pd.DataFrame(
            {"signal_type": ["buy"]}, index=pd.DatetimeIndex(["2024-01-01"], tz=timezone.utc)
        )

        result = strategy.write_signals(signals, "AAPL")

        assert result is False
        mock_dependencies["influx_instance"].write.assert_not_called()

    def test_write_signals_invalid_index(self, mock_dependencies):
        """Test writing signals with non-datetime index."""
        strategy = ConcreteStrategy()
        signals = pd.DataFrame({"signal_type": ["buy"], "price": [100.0]})

        result = strategy.write_signals(signals, "AAPL")

        assert result is False

    def test_write_signals_adds_metadata(self, mock_dependencies):
        """Test that signals have ticker, strategy, and timestamp metadata added."""
        mock_dependencies["influx_instance"].write.return_value = True

        strategy = ConcreteStrategy(strategy_name="sma_crossover")
        signals = pd.DataFrame(
            {"signal_type": ["buy"], "price": [100.0]},
            index=pd.DatetimeIndex(["2024-01-01"], tz=timezone.utc),
        )

        strategy.write_signals(signals, "AAPL")

        call_args = mock_dependencies["influx_instance"].write.call_args
        data_written = call_args[1]["data"]

        assert isinstance(data_written, list)
        assert len(data_written) == 1
        assert "datetime" in data_written[0]
        assert "signal_type" in data_written[0]
        assert "price" in data_written[0]
        assert "ticker" in data_written[0]
        assert "strategy" in data_written[0]
        assert "generated_at" in data_written[0]

    def test_write_signals_exception(self, mock_dependencies):
        """Test signal writing when exception occurs."""
        mock_dependencies["influx_instance"].write.side_effect = Exception("Write failed")

        strategy = ConcreteStrategy()
        signals = pd.DataFrame(
            {"signal_type": ["buy"], "price": [100.0]},
            index=pd.DatetimeIndex(["2024-01-01"], tz=timezone.utc),
        )

        result = strategy.write_signals(signals, "AAPL")

        assert result is False


class TestRunStrategy:
    """Test single-ticker strategy execution workflow."""

    def test_run_strategy_success(self, mock_dependencies, sample_ohlcv_data):
        """Test complete workflow for single ticker."""
        mock_dependencies[
            "influx_instance"
        ].query.return_value = sample_ohlcv_data.reset_index().rename(columns={"index": "time"})
        mock_dependencies["influx_instance"].write.return_value = True

        strategy = ConcreteStrategy()
        result = strategy.run_strategy("AAPL")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # ConcreteStrategy generates 2 signals
        assert "ticker" in result.columns
        assert "signal_time" in result.columns
        assert (result["ticker"] == "AAPL").all()

    def test_run_strategy_no_ohlcv_data(self, mock_dependencies):
        """Test workflow when no OHLCV data is available."""
        mock_dependencies["influx_instance"].query.return_value = None

        strategy = ConcreteStrategy()
        result = strategy.run_strategy("AAPL")

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_run_strategy_empty_ohlcv_data(self, mock_dependencies):
        """Test workflow when OHLCV data is empty."""
        mock_dependencies["influx_instance"].query.return_value = pd.DataFrame()

        strategy = ConcreteStrategy()
        result = strategy.run_strategy("AAPL")

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_run_strategy_signal_generation_error(self, mock_dependencies, sample_ohlcv_data):
        """Test workflow when signal generation raises exception."""
        mock_dependencies[
            "influx_instance"
        ].query.return_value = sample_ohlcv_data.reset_index().rename(columns={"index": "time"})

        strategy = ConcreteStrategy()
        # Patch generate_signals to raise exception
        with patch.object(strategy, "generate_signals", side_effect=Exception("Generation failed")):
            result = strategy.run_strategy("AAPL")

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_run_strategy_no_signals_generated(self, mock_dependencies):
        """Test workflow when no signals are generated."""
        # Return OHLCV data with only 1 row (ConcreteStrategy needs 2+)
        ohlcv_data = pd.DataFrame(
            {"close": [100.0], "ticker": ["AAPL"]},
            index=pd.DatetimeIndex(["2024-01-01"], tz=timezone.utc, name="time"),
        )
        mock_dependencies["influx_instance"].query.return_value = ohlcv_data.reset_index()

        strategy = ConcreteStrategy()
        result = strategy.run_strategy("AAPL")

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_run_strategy_write_failure(self, mock_dependencies, sample_ohlcv_data):
        """Test workflow continues and returns summary even if write fails."""
        mock_dependencies[
            "influx_instance"
        ].query.return_value = sample_ohlcv_data.reset_index().rename(columns={"index": "time"})
        mock_dependencies["influx_instance"].write.return_value = False

        strategy = ConcreteStrategy()
        result = strategy.run_strategy("AAPL")

        # Should still return summary even though write failed
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2


class TestRunStrategyMulti:
    """Test multi-ticker strategy execution."""

    def test_run_strategy_multi_sequential(self, mock_dependencies, sample_ohlcv_data):
        """Test sequential processing of multiple tickers."""
        mock_dependencies[
            "influx_instance"
        ].query.return_value = sample_ohlcv_data.reset_index().rename(columns={"index": "time"})
        mock_dependencies["influx_instance"].write.return_value = True

        strategy = ConcreteStrategy(use_threading=False)
        tickers = ["AAPL", "MSFT", "GOOGL"]

        result = strategy.run_strategy_multi(tickers)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 6  # 2 signals per ticker * 3 tickers
        assert set(result["ticker"].unique()) == set(tickers)

    def test_run_strategy_multi_threaded(self, mock_dependencies, sample_ohlcv_data):
        """Test threaded processing of multiple tickers."""
        mock_dependencies[
            "influx_instance"
        ].query.return_value = sample_ohlcv_data.reset_index().rename(columns={"index": "time"})
        mock_dependencies["influx_instance"].write.return_value = True

        # Mock ThreadManager behavior
        def mock_get_all_results():
            return {
                "strategy-AAPL": {
                    "success": True,
                    "summary": pd.DataFrame(
                        {
                            "ticker": ["AAPL", "AAPL"],
                            "signal_type": ["buy", "sell"],
                            "price": [100.0, 105.0],
                            "signal_time": [
                                pd.Timestamp("2024-01-01", tz=timezone.utc),
                                pd.Timestamp("2024-01-05", tz=timezone.utc),
                            ],
                        }
                    ),
                },
                "strategy-MSFT": {
                    "success": True,
                    "summary": pd.DataFrame(
                        {
                            "ticker": ["MSFT", "MSFT"],
                            "signal_type": ["buy", "sell"],
                            "price": [200.0, 210.0],
                            "signal_time": [
                                pd.Timestamp("2024-01-01", tz=timezone.utc),
                                pd.Timestamp("2024-01-05", tz=timezone.utc),
                            ],
                        }
                    ),
                },
            }

        mock_dependencies["thread_instance"].get_all_results.side_effect = mock_get_all_results

        strategy = ConcreteStrategy(use_threading=True)
        tickers = ["AAPL", "MSFT"]

        result = strategy.run_strategy_multi(tickers)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4
        mock_dependencies["thread_instance"].wait_for_all_threads.assert_called_once()
        mock_dependencies["influx_instance"].wait_for_batches.assert_called_once()

    def test_run_strategy_multi_no_signals(self, mock_dependencies):
        """Test multi-ticker when no signals are generated."""
        mock_dependencies["influx_instance"].query.return_value = None

        strategy = ConcreteStrategy(use_threading=False)
        result = strategy.run_strategy_multi(["AAPL", "MSFT"])

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_run_strategy_multi_partial_success(self, mock_dependencies, sample_ohlcv_data):
        """Test multi-ticker when only some tickers generate signals."""
        # First query succeeds, second fails
        mock_dependencies["influx_instance"].query.side_effect = [
            sample_ohlcv_data.reset_index().rename(columns={"index": "time"}),
            None,
            sample_ohlcv_data.reset_index().rename(columns={"index": "time"}),
        ]
        mock_dependencies["influx_instance"].write.return_value = True

        strategy = ConcreteStrategy(use_threading=False)
        result = strategy.run_strategy_multi(["AAPL", "FAIL", "GOOGL"])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4  # 2 signals for AAPL, 0 for FAIL, 2 for GOOGL

    def test_run_strategy_multi_threaded_with_failures(self, mock_dependencies):
        """Test threaded multi-ticker with some thread failures."""

        def mock_get_all_results():
            return {
                "strategy-AAPL": {
                    "success": True,
                    "summary": pd.DataFrame(
                        {
                            "ticker": ["AAPL"],
                            "signal_type": ["buy"],
                            "price": [100.0],
                            "signal_time": [pd.Timestamp("2024-01-01", tz=timezone.utc)],
                        }
                    ),
                },
                "strategy-FAIL": {"success": False, "error": "Query failed"},
                "strategy-EMPTY": {"success": True, "summary": pd.DataFrame()},
            }

        mock_dependencies["thread_instance"].get_all_results.side_effect = mock_get_all_results

        strategy = ConcreteStrategy(use_threading=True)
        result = strategy.run_strategy_multi(["AAPL", "FAIL", "EMPTY"])

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1  # Only AAPL succeeded with signals


class TestQuerySignals:
    """Test querying historical signals from InfluxDB."""

    def test_query_signals_no_filters(self, mock_dependencies):
        """Test querying all signals for the strategy."""
        mock_signals = pd.DataFrame({"ticker": ["AAPL"], "signal_type": ["buy"], "price": [100.0]})
        mock_dependencies["influx_instance"].query.return_value = mock_signals

        strategy = ConcreteStrategy(strategy_name="sma_crossover")
        result = strategy.query_signals()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        call_args = mock_dependencies["influx_instance"].query.call_args
        query = call_args[0][0]
        assert "strategy = 'sma_crossover'" in query

    def test_query_signals_with_ticker_filter(self, mock_dependencies):
        """Test querying signals filtered by ticker."""
        mock_signals = pd.DataFrame({"ticker": ["AAPL"], "signal_type": ["buy"]})
        mock_dependencies["influx_instance"].query.return_value = mock_signals

        strategy = ConcreteStrategy()
        strategy.query_signals(ticker="AAPL")

        call_args = mock_dependencies["influx_instance"].query.call_args
        query = call_args[0][0]
        assert "ticker = 'AAPL'" in query

    def test_query_signals_with_time_filters(self, mock_dependencies):
        """Test querying signals with time range filters."""
        mock_dependencies["influx_instance"].query.return_value = pd.DataFrame()

        strategy = ConcreteStrategy()
        strategy.query_signals(start_time="2024-01-01", end_time="2024-01-31")

        call_args = mock_dependencies["influx_instance"].query.call_args
        query = call_args[0][0]
        assert "time >= '2024-01-01'" in query
        assert "time <= '2024-01-31'" in query

    def test_query_signals_with_signal_type_filter(self, mock_dependencies):
        """Test querying signals filtered by signal type."""
        mock_dependencies["influx_instance"].query.return_value = pd.DataFrame()

        strategy = ConcreteStrategy()
        strategy.query_signals(signal_type="buy")

        call_args = mock_dependencies["influx_instance"].query.call_args
        query = call_args[0][0]
        assert "signal_type = 'buy'" in query

    def test_query_signals_no_results(self, mock_dependencies):
        """Test querying signals when no results found."""
        mock_dependencies["influx_instance"].query.return_value = None

        strategy = ConcreteStrategy()
        result = strategy.query_signals(ticker="NONEXISTENT")

        assert result is None

    def test_query_signals_exception(self, mock_dependencies):
        """Test querying signals when exception occurs."""
        mock_dependencies["influx_instance"].query.side_effect = Exception("Query failed")

        strategy = ConcreteStrategy()
        result = strategy.query_signals()

        assert result is None


class TestStrategyWriteConfig:
    """Test strategy_write_config module-level configuration."""

    def test_strategy_write_config_exists(self):
        """Test that strategy_write_config is defined."""
        assert strategy_write_config is not None

    def test_strategy_write_config_values(self):
        """Test strategy_write_config has appropriate values."""
        assert strategy_write_config.batch_size == 50000
        assert strategy_write_config.flush_interval == 3000
        assert strategy_write_config.jitter_interval == 500
        assert strategy_write_config.retry_interval == 8000
        assert strategy_write_config.max_retries == 3
        assert strategy_write_config.max_retry_delay == 25000
        assert strategy_write_config.exponential_base == 2
