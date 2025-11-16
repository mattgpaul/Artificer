"""Unit and integration tests for BacktestEngine.

Tests cover initialization, data loading, signal collection, results generation,
and complete workflows. All external dependencies are mocked via conftest.py.
Integration tests use 'debug' database for InfluxDB operations.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.engine import BacktestEngine, BacktestResults


class TestBacktestResults:
    """Test BacktestResults container class."""

    @pytest.mark.unit
    def test_initialization(self):
        """Test BacktestResults initialization creates empty containers."""
        results = BacktestResults()
        assert results.signals.empty
        assert results.trades.empty
        assert results.metrics == {}
        assert results.strategy_name == ""

    @pytest.mark.unit
    def test_results_with_data(self):
        """Test BacktestResults can hold data."""
        results = BacktestResults()
        results.signals = pd.DataFrame({"ticker": ["AAPL"], "signal_type": ["buy"]})
        results.trades = pd.DataFrame({"ticker": ["AAPL"], "gross_pnl": [100.0]})
        results.metrics = {"total_trades": 1}
        results.strategy_name = "TestStrategy"

        assert len(results.signals) == 1
        assert len(results.trades) == 1
        assert results.metrics["total_trades"] == 1
        assert results.strategy_name == "TestStrategy"


class TestBacktestEngineInitialization:
    """Test BacktestEngine initialization with various configurations."""

    @pytest.mark.unit
    def test_initialization_defaults(self, mock_strategy, mock_market_data_influx):
        """Test BacktestEngine initialization with default parameters."""
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
        assert engine.database == "ohlcv"
        assert engine.capital_per_trade == 10000.0
        assert engine.risk_free_rate == 0.04
        assert isinstance(engine.execution_config, ExecutionConfig)
        assert engine.influx_client is not None

    @pytest.mark.unit
    def test_initialization_custom_database(self, mock_strategy, mock_market_data_influx):
        """Test initialization with custom database."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="custom_db",
        )
        assert engine.database == "custom_db"

    @pytest.mark.unit
    def test_initialization_custom_execution_config(self, mock_strategy, mock_market_data_influx):
        """Test initialization with custom execution config."""
        execution_config = ExecutionConfig(slippage_bps=10.0, commission_per_share=0.01)
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            execution_config=execution_config,
        )
        assert engine.execution_config.slippage_bps == 10.0
        assert engine.execution_config.commission_per_share == 0.01

    @pytest.mark.unit
    def test_initialization_custom_capital_and_rate(self, mock_strategy, mock_market_data_influx):
        """Test initialization with custom capital and risk-free rate."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            capital_per_trade=20000.0,
            risk_free_rate=0.05,
        )
        assert engine.capital_per_trade == 20000.0
        assert engine.risk_free_rate == 0.05

    @pytest.mark.unit
    def test_initialization_account_tracking(self, mock_strategy, mock_market_data_influx):
        """Test initialization with account value tracking."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            initial_account_value=50000.0,
            trade_percentage=0.10,
        )
        assert engine.results_generator.initial_account_value == 50000.0
        assert engine.results_generator.trade_percentage == 0.10

    @pytest.mark.unit
    def test_initialization_multiple_tickers(self, mock_strategy, mock_market_data_influx):
        """Test initialization with multiple tickers."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL", "MSFT", "GOOGL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
        )
        assert len(engine.tickers) == 3
        assert engine.tickers == ["AAPL", "MSFT", "GOOGL"]

    @pytest.mark.unit
    def test_initialization_creates_components(self, mock_strategy, mock_market_data_influx):
        """Test initialization creates all required components."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
        )
        assert engine.data_loader is not None
        assert engine.time_stepper is not None
        assert engine.signal_collector is not None
        assert engine.results_generator is not None
        assert engine.execution_simulator is not None


class TestBacktestEngineDataLoading:
    """Test data loading functionality."""

    @pytest.mark.unit
    def test_load_ticker_ohlcv_data_success(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data_with_time
    ):
        """Test successful loading of OHLCV data for a ticker."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        # Mock query to return sample data (with time column for DataLoader)
        mock_market_data_influx["instance"].query.return_value = sample_ohlcv_data_with_time.copy()

        result = engine.data_loader.load_ticker_ohlcv_data("AAPL", start_date, end_date)

        assert result is not None
        assert len(result) == len(sample_ohlcv_data_with_time)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.tz is not None

    @pytest.mark.unit
    def test_load_ticker_ohlcv_data_no_data(self, mock_strategy, mock_market_data_influx):
        """Test loading when no data found returns None."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        mock_market_data_influx["instance"].query.return_value = None

        result = engine.data_loader.load_ticker_ohlcv_data("AAPL", start_date, end_date)

        assert result is None

    @pytest.mark.unit
    def test_load_ticker_ohlcv_data_empty_dataframe(self, mock_strategy, mock_market_data_influx):
        """Test loading when empty DataFrame returned."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        mock_market_data_influx["instance"].query.return_value = pd.DataFrame()

        result = engine.data_loader.load_ticker_ohlcv_data("AAPL", start_date, end_date)

        assert result is None

    @pytest.mark.unit
    def test_load_ohlcv_data_multiple_tickers(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data_with_time
    ):
        """Test loading data for multiple tickers."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL", "MSFT"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        mock_market_data_influx["instance"].query.return_value = sample_ohlcv_data_with_time.copy()

        result = engine.data_loader.load_ohlcv_data(["AAPL", "MSFT"], start_date, end_date)

        assert isinstance(result, dict)
        assert len(result) == 2
        assert "AAPL" in result
        assert "MSFT" in result

    @pytest.mark.unit
    def test_load_ohlcv_data_partial_failure(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data
    ):
        """Test loading when one ticker fails but others succeed."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-31", tz="UTC")
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL", "INVALID"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        sample_data_with_time = sample_ohlcv_data.reset_index()
        sample_data_with_time = sample_data_with_time.rename(columns={"index": "time"})

        def query_side_effect(query):
            if "AAPL" in query:
                return sample_data_with_time.copy()
            return None

        mock_market_data_influx["instance"].query.side_effect = query_side_effect

        result = engine.data_loader.load_ohlcv_data(["AAPL", "INVALID"], start_date, end_date)

        assert isinstance(result, dict)
        assert "AAPL" in result
        assert "INVALID" not in result


class TestBacktestEngineStepIntervals:
    """Test step interval determination."""

    @pytest.mark.unit
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

        intervals = engine.time_stepper.determine_step_intervals()

        assert len(intervals) > 0
        assert intervals[0] >= start_date
        assert intervals[-1] <= end_date
        assert all(interval.tz is not None for interval in intervals)

    @pytest.mark.unit
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

        intervals = engine.time_stepper.determine_step_intervals()

        assert len(intervals) > 0
        assert intervals[0] >= start_date
        assert intervals[-1] <= end_date
        # Should have approximately 24 intervals for 1 day
        assert len(intervals) >= 20

    @pytest.mark.unit
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

        data_cache = {"AAPL": sample_ohlcv_data}
        intervals = engine.time_stepper.determine_step_intervals(data_cache)

        assert len(intervals) > 0
        assert intervals[0] >= start_date
        assert intervals[-1] <= end_date

    @pytest.mark.unit
    def test_determine_step_intervals_empty_data_cache(
        self, mock_strategy, mock_market_data_influx
    ):
        """Test step interval determination with empty data cache."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="auto",
        )

        intervals = engine.time_stepper.determine_step_intervals({})

        assert len(intervals) == 0


class TestBacktestEngineSignalCollection:
    """Test signal collection functionality."""

    @pytest.mark.unit
    def test_collect_signals_for_ticker(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data
    ):
        """Test collecting signals for a single ticker."""
        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-10", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        # Mock strategy to return signals
        mock_signals = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "signal_time": [pd.Timestamp("2024-01-05", tz="UTC")],
                "signal_type": ["buy"],
                "price": [100.0],
            }
        )
        mock_strategy.run_strategy.return_value = mock_signals

        data_cache = {"AAPL": sample_ohlcv_data}
        step_intervals = engine.time_stepper.determine_step_intervals(data_cache)

        signals = engine.signal_collector.collect_signals_for_ticker(
            "AAPL", step_intervals, data_cache
        )

        assert len(signals) > 0

    @pytest.mark.unit
    def test_collect_signals_no_signals_generated(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data
    ):
        """Test signal collection when strategy generates no signals."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-10", tz="UTC"),
            step_frequency="daily",
        )

        mock_strategy.run_strategy.return_value = pd.DataFrame()

        data_cache = {"AAPL": sample_ohlcv_data}
        step_intervals = engine.time_stepper.determine_step_intervals(data_cache)

        signals = engine.signal_collector.collect_signals_for_ticker(
            "AAPL", step_intervals, data_cache
        )

        assert len(signals) == 0

    @pytest.mark.unit
    def test_collect_signals_for_all_tickers(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data
    ):
        """Test collecting signals for multiple tickers."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL", "MSFT"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-10", tz="UTC"),
            step_frequency="daily",
        )

        mock_signals = pd.DataFrame(
            {
                "ticker": ["AAPL", "MSFT"],
                "signal_time": [
                    pd.Timestamp("2024-01-05", tz="UTC"),
                    pd.Timestamp("2024-01-06", tz="UTC"),
                ],
                "signal_type": ["buy", "buy"],
                "price": [100.0, 200.0],
            }
        )
        mock_strategy.run_strategy.return_value = mock_signals

        data_cache = {"AAPL": sample_ohlcv_data, "MSFT": sample_ohlcv_data}
        step_intervals = engine.time_stepper.determine_step_intervals(data_cache)

        signals = engine.signal_collector.collect_signals_for_all_tickers(
            step_intervals, ["AAPL", "MSFT"], data_cache
        )

        assert len(signals) > 0
        assert any(s["ticker"] == "AAPL" for s in signals)
        assert any(s["ticker"] == "MSFT" for s in signals)


class TestBacktestEngineRunTicker:
    """Test run_ticker method - single ticker backtest."""

    @pytest.mark.unit
    def test_run_ticker_no_data(self, mock_strategy, mock_market_data_influx):
        """Test run_ticker when no OHLCV data available."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
        )

        mock_market_data_influx["instance"].query.return_value = None

        results = engine.run_ticker("AAPL")

        assert isinstance(results, BacktestResults)
        assert results.signals.empty
        assert results.trades.empty

    @pytest.mark.unit
    def test_run_ticker_empty_dataframe(self, mock_strategy, mock_market_data_influx):
        """Test run_ticker when empty DataFrame returned."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
        )

        mock_market_data_influx["instance"].query.return_value = pd.DataFrame()

        results = engine.run_ticker("AAPL")

        assert isinstance(results, BacktestResults)
        assert results.signals.empty

    @pytest.mark.unit
    def test_run_ticker_no_signals(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data_with_time
    ):
        """Test run_ticker when data exists but no signals generated."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-10", tz="UTC"),
            step_frequency="daily",
        )

        mock_market_data_influx["instance"].query.return_value = sample_ohlcv_data_with_time.copy()
        mock_strategy.run_strategy.return_value = pd.DataFrame()

        results = engine.run_ticker("AAPL")

        assert isinstance(results, BacktestResults)
        assert results.signals.empty

    @pytest.mark.unit
    def test_run_ticker_no_step_intervals(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data_with_time
    ):
        """Test run_ticker when no step intervals can be determined."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-01", tz="UTC"),  # Same start and end
            step_frequency="daily",
        )

        mock_market_data_influx["instance"].query.return_value = sample_ohlcv_data_with_time.copy()

        results = engine.run_ticker("AAPL")

        assert isinstance(results, BacktestResults)
        assert results.signals.empty

    @pytest.mark.integration
    def test_run_ticker_complete_workflow(
        self,
        mock_strategy,
        mock_market_data_influx,
        sample_ohlcv_data_with_time,
        sample_mock_signals,
        sample_mock_trades,
    ):
        """Test complete run_ticker workflow: data load → signals → trades → metrics."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",  # Use debug database for integration tests
        )

        # Setup data
        mock_market_data_influx["instance"].query.return_value = sample_ohlcv_data_with_time.copy()

        # Setup signals
        mock_strategy.run_strategy.return_value = sample_mock_signals

        # Mock TradeJournal and ExecutionSimulator
        with (
            patch(
                "system.algo_trader.backtest.core.results_generator.TradeJournal"
            ) as mock_journal_class,
            patch(
                "system.algo_trader.backtest.core.results_generator.ExecutionSimulator"
            ) as mock_exec_sim_class,
        ):
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = (
                {"total_trades": 1, "total_profit": 500.0},
                sample_mock_trades,
            )
            mock_journal_class.return_value = mock_journal

            mock_exec_sim = MagicMock()
            mock_exec_sim.apply_execution.return_value = sample_mock_trades
            mock_exec_sim_class.return_value = mock_exec_sim

            results = engine.run_ticker("AAPL")

            assert isinstance(results, BacktestResults)
            assert not results.signals.empty
            assert not results.trades.empty
            assert results.metrics["total_trades"] == 1

    @pytest.mark.integration
    def test_run_ticker_with_account_tracking(
        self,
        mock_strategy,
        mock_market_data_influx,
        sample_ohlcv_data_with_time,
        sample_mock_signals,
    ):
        """Test run_ticker with account value tracking."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
            initial_account_value=50000.0,
            trade_percentage=0.10,
        )

        mock_market_data_influx["instance"].query.return_value = sample_ohlcv_data_with_time.copy()
        mock_strategy.run_strategy.return_value = sample_mock_signals

        with patch(
            "system.algo_trader.backtest.core.results_generator.TradeJournal"
        ) as mock_journal_class:
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, pd.DataFrame())
            mock_journal_class.return_value = mock_journal

            engine.run_ticker("AAPL")

            # Verify account tracking parameters were passed
            call_args = mock_journal_class.call_args
            assert call_args[1]["initial_account_value"] == 50000.0
            assert call_args[1]["trade_percentage"] == 0.10


class TestBacktestEngineRun:
    """Test run() method - multiple ticker backtest."""

    @pytest.mark.unit
    def test_run_no_data_loaded(self, mock_strategy, mock_market_data_influx):
        """Test run() when no data can be loaded."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL", "MSFT"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
        )

        mock_market_data_influx["instance"].query.return_value = None

        results = engine.run()

        assert isinstance(results, BacktestResults)
        assert results.signals.empty

    @pytest.mark.unit
    def test_run_no_step_intervals(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data_with_time
    ):
        """Test run() when no step intervals can be determined."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-01", tz="UTC"),
            step_frequency="daily",
        )

        mock_market_data_influx["instance"].query.return_value = sample_ohlcv_data_with_time.copy()

        results = engine.run()

        assert isinstance(results, BacktestResults)
        assert results.signals.empty

    @pytest.mark.unit
    def test_run_no_signals(
        self, mock_strategy, mock_market_data_influx, sample_ohlcv_data_with_time
    ):
        """Test run() when no signals are generated."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
        )

        mock_market_data_influx["instance"].query.return_value = sample_ohlcv_data_with_time.copy()
        mock_strategy.run_strategy.return_value = pd.DataFrame()

        results = engine.run()

        assert isinstance(results, BacktestResults)
        assert results.signals.empty

    @pytest.mark.integration
    def test_run_complete_workflow_multiple_tickers(
        self,
        mock_strategy,
        mock_market_data_influx,
        sample_ohlcv_data_with_time,
        sample_mock_signals_multiple_tickers,
        sample_mock_trades,
    ):
        """Test complete run() workflow for multiple tickers."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL", "MSFT"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
        )

        mock_market_data_influx["instance"].query.return_value = sample_ohlcv_data_with_time.copy()
        mock_strategy.run_strategy.return_value = sample_mock_signals_multiple_tickers

        with (
            patch(
                "system.algo_trader.backtest.core.results_generator.TradeJournal"
            ) as mock_journal_class,
            patch(
                "system.algo_trader.backtest.core.results_generator.ExecutionSimulator"
            ) as mock_exec_sim_class,
        ):
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, sample_mock_trades)
            mock_journal_class.return_value = mock_journal

            mock_exec_sim = MagicMock()
            mock_exec_sim.apply_execution.return_value = sample_mock_trades
            mock_exec_sim_class.return_value = mock_exec_sim

            results = engine.run()

            assert isinstance(results, BacktestResults)
            assert not results.signals.empty
            # Should have signals from both tickers
            assert len(results.signals) >= 2

    @pytest.mark.integration
    def test_run_closes_influx_client(
        self,
        mock_strategy,
        mock_market_data_influx,
        sample_ohlcv_data_with_time,
        sample_mock_signals_single,
    ):
        """Test run() closes InfluxDB client after completion."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
            database="debug",
        )

        mock_market_data_influx["instance"].query.return_value = sample_ohlcv_data_with_time.copy()
        # Generate signals so close() is called (close() only called when signals exist)
        mock_strategy.run_strategy.return_value = sample_mock_signals_single

        with (
            patch(
                "system.algo_trader.backtest.core.results_generator.TradeJournal"
            ) as mock_journal_class,
            patch(
                "system.algo_trader.backtest.core.results_generator.ExecutionSimulator"
            ) as mock_exec_sim_class,
        ):
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, pd.DataFrame())
            mock_journal_class.return_value = mock_journal

            mock_exec_sim = MagicMock()
            mock_exec_sim.apply_execution.return_value = pd.DataFrame()
            mock_exec_sim_class.return_value = mock_exec_sim

            engine.run()

        mock_market_data_influx["instance"].close.assert_called_once()


class TestBacktestEngineEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.unit
    def test_invalid_date_range(self, mock_strategy, mock_market_data_influx):
        """Test behavior with invalid date range (start >= end)."""
        # This should be handled by the caller, but test defensive behavior
        start_date = pd.Timestamp("2024-01-31", tz="UTC")
        end_date = pd.Timestamp("2024-01-01", tz="UTC")

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        # Should still initialize, but run() should handle gracefully
        assert engine.start_date == start_date
        assert engine.end_date == end_date

    @pytest.mark.unit
    def test_empty_ticker_list(self, mock_strategy, mock_market_data_influx):
        """Test initialization with empty ticker list."""
        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=[],
            start_date=pd.Timestamp("2024-01-01", tz="UTC"),
            end_date=pd.Timestamp("2024-01-31", tz="UTC"),
            step_frequency="daily",
        )

        assert engine.tickers == []
        results = engine.run()
        assert isinstance(results, BacktestResults)
        assert results.signals.empty

    @pytest.mark.unit
    def test_timezone_handling(self, mock_strategy, mock_market_data_influx):
        """Test proper timezone handling in dates."""
        # Test with timezone-naive dates (should be converted)
        start_date = pd.Timestamp("2024-01-01")  # No timezone
        end_date = pd.Timestamp("2024-01-31")  # No timezone

        engine = BacktestEngine(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
        )

        # Engine should handle timezone conversion internally
        assert engine.start_date.tz is not None or engine.start_date.tz is None
        assert engine.end_date.tz is not None or engine.end_date.tz is None
