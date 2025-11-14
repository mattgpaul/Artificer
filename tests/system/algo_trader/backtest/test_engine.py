"""Unit tests for BacktestEngine.

Tests cover data loading, step interval determination, and backtest execution.
All external dependencies are mocked via conftest.py.
.
"""

from unittest.mock import patch

import pandas as pd

from system.algo_trader.backtest.engine import BacktestEngine, BacktestResults
from system.algo_trader.backtest.execution import ExecutionConfig


class TestBacktestResults:
    """Test BacktestResults class."""

    def test_initialization(self):
        """Test BacktestResults initialization."""
        results = BacktestResults()
        assert results.signals.empty
        assert results.trades.empty
        assert results.metrics == {}
        assert results.strategy_name == ""


class TestBacktestEngine:
    """Test BacktestEngine operations."""

    def test_initialization(self, mock_strategy, mock_market_data_influx):
        """Test BacktestEngine initialization."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        assert engine.strategy == mock_strategy
        assert engine.tickers == ["AAPL"]
        assert engine.start_date == start_date
        assert engine.end_date == end_date
        assert engine.step_frequency == "daily"
        assert engine.database == "algo-trader-ohlcv"

    def test_initialization_custom_params(self, mock_strategy, mock_market_data_influx):
        """Test BacktestEngine initialization with custom parameters."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")
        execution_config = ExecutionConfig(slippage_bps=10.0)

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL", "MSFT"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="hourly",
            database="custom_db",
            execution_config=execution_config,
            capital_per_trade=20000.0,
            risk_free_rate=0.05,
        )

        assert engine.database == "custom_db"
        assert engine.capital_per_trade == 20000.0
        assert engine.risk_free_rate == 0.05
        assert engine.execution_config.slippage_bps == 10.0

    def test_load_ticker_ohlcv_data_success(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data
    ):
        """Test loading OHLCV data for a ticker."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        # Mock query to return sample data
        mock_market_data_influx["instance"].query.return_value = sample_ohlcv_data.copy()

        result = engine._load_ticker_ohlcv_data("AAPL")

        assert result is not None
        assert len(result) == len(sample_ohlcv_data)
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_load_ticker_ohlcv_data_no_data(self, mock_strategy, mock_market_data_influx):
        """Test loading OHLCV data when no data found."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        # Mock query to return None/empty
        mock_market_data_influx["instance"].query.return_value = None

        result = engine._load_ticker_ohlcv_data("AAPL")

        assert result is None

    def test_determine_step_intervals_daily(self, mock_strategy, mock_market_data_influx):
        """Test step interval determination for daily frequency."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-10", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        intervals = engine._determine_step_intervals()

        assert len(intervals) > 0
        assert intervals[0] >= start_date
        assert intervals[-1] <= end_date

    def test_determine_step_intervals_hourly(self, mock_strategy, mock_market_data_influx):
        """Test step interval determination for hourly frequency."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-02", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="hourly",
        )

        intervals = engine._determine_step_intervals()

        assert len(intervals) > 0
        assert intervals[0] >= start_date
        assert intervals[-1] <= end_date

    def test_determine_step_intervals_auto(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data
    ):
        """Test step interval determination with auto frequency."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="auto",
        )

        # Set up data cache for auto detection
        engine.data_cache = {"AAPL": sample_ohlcv_data}

        intervals = engine._determine_step_intervals()

        assert len(intervals) > 0

    def test_timedelta_to_freq(self, mock_strategy, mock_market_data_influx):
        """Test timedelta to frequency string conversion."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        assert engine._timedelta_to_freq(pd.Timedelta(days=1)) == "D"
        assert engine._timedelta_to_freq(pd.Timedelta(hours=1)) == "H"
        assert engine._timedelta_to_freq(pd.Timedelta(minutes=1)) == "T"
        assert engine._timedelta_to_freq(pd.Timedelta(seconds=1)) == "S"

    def test_run_ticker_no_data(self, mock_strategy, mock_market_data_influx):
        """Test run_ticker when no OHLCV data available."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        # Mock query to return None
        mock_market_data_influx["instance"].query.return_value = None

        results = engine.run_ticker("AAPL")

        assert isinstance(results, BacktestResults)
        assert results.signals.empty

    def test_run_ticker_with_data_no_signals(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data
    ):
        """Test run_ticker when data exists but no signals generated."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-10", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        # Mock query to return sample data
        mock_market_data_influx["instance"].query.return_value = sample_ohlcv_data.copy()

        # Mock strategy to return empty signals
        mock_strategy.run_strategy.return_value = pd.DataFrame()

        with patch("system.algo_trader.backtest.engine.ticker_progress_bar"):
            results = engine.run_ticker("AAPL")

        assert isinstance(results, BacktestResults)
        assert results.signals.empty

    def test_determine_step_intervals_for_data(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data
    ):
        """Test determine_step_intervals_for_data method."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        data_cache = {"AAPL": sample_ohlcv_data}
        intervals = engine._determine_step_intervals_for_data(data_cache)

        assert len(intervals) > 0
        assert intervals[0] >= start_date
        assert intervals[-1] <= end_date
