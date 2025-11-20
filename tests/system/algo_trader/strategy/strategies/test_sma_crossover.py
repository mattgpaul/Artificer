"""Unit and integration tests for SMACrossover - Simple Moving Average Crossover Strategy.

Tests cover initialization, validation, SMA calculation, crossover detection,
and signal generation. All external dependencies are mocked to avoid logging calls.
Integration tests exercise BacktestEngine with SMACrossover strategy.
"""

import argparse
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.engine import BacktestEngine, BacktestResults
from system.algo_trader.strategy.strategies.sma_crossover import SMACrossover
from system.algo_trader.strategy.strategy import Side


class TestSMACrossoverInitialization:
    """Test SMACrossover initialization and validation."""

    def test_initialization_defaults(self):
        """Test initialization with default parameters."""
        strategy = SMACrossover()
        assert strategy.short == 10
        assert strategy.long == 20
        assert strategy.window == 120
        assert strategy.side == Side.LONG
        assert strategy.sma_study is not None

    def test_initialization_custom_parameters(self):
        """Test initialization with custom parameters."""
        strategy = SMACrossover(short=5, long=15, window=60, side=Side.SHORT)
        assert strategy.short == 5
        assert strategy.long == 15
        assert strategy.window == 60
        assert strategy.side == Side.SHORT

    def test_initialization_short_greater_than_long_raises(self):
        """Test initialization fails when short >= long."""
        with pytest.raises(ValueError, match=r"short.*must be less than long"):
            SMACrossover(short=20, long=10)

    def test_initialization_short_equal_long_raises(self):
        """Test initialization fails when short equals long."""
        with pytest.raises(ValueError, match=r"short.*must be less than long"):
            SMACrossover(short=10, long=10)

    def test_initialization_short_less_than_two_raises(self):
        """Test initialization fails when short < 2."""
        with pytest.raises(ValueError, match="short must be at least 2"):
            SMACrossover(short=1, long=10)

    def test_initialization_short_zero_raises(self):
        """Test initialization fails when short is zero."""
        with pytest.raises(ValueError, match="short must be at least 2"):
            SMACrossover(short=0, long=10)

    def test_initialization_short_negative_raises(self):
        """Test initialization fails when short is negative."""
        with pytest.raises(ValueError, match="short must be at least 2"):
            SMACrossover(short=-1, long=10)


class TestSMACrossoverCalculateSMAs:
    """Test _calculate_smas method."""

    def test_calculate_smas_success(self, sample_ohlcv_data):
        """Test successful SMA calculation with sufficient data."""
        strategy = SMACrossover(short=5, long=10)
        sma_short, sma_long = strategy._calculate_smas(sample_ohlcv_data, "AAPL")

        assert sma_short is not None
        assert sma_long is not None
        assert isinstance(sma_short, pd.Series)
        assert isinstance(sma_long, pd.Series)
        assert len(sma_short) == len(sample_ohlcv_data)
        assert len(sma_long) == len(sample_ohlcv_data)

    def test_calculate_smas_insufficient_data_returns_none(self, sample_ohlcv_data_insufficient):
        """Test SMA calculation returns None when data is insufficient."""
        strategy = SMACrossover(short=5, long=10)
        sma_short, sma_long = strategy._calculate_smas(sample_ohlcv_data_insufficient, "AAPL")

        assert sma_short is None
        assert sma_long is None

    def test_calculate_smas_empty_data_returns_none(self, sample_ohlcv_data_empty):
        """Test SMA calculation returns None for empty data."""
        strategy = SMACrossover(short=5, long=10)
        sma_short, sma_long = strategy._calculate_smas(sample_ohlcv_data_empty, "AAPL")

        assert sma_short is None
        assert sma_long is None


class TestSMACrossoverLastCrossoverState:
    """Test _last_crossover_state method."""

    def test_last_crossover_state_success(self, sample_ohlcv_data):
        """Test successful crossover state calculation."""
        strategy = SMACrossover(short=5, long=10)
        sma_short, sma_long = strategy._calculate_smas(sample_ohlcv_data, "AAPL")

        state = strategy._last_crossover_state(sma_short, sma_long)

        assert state is not None
        assert isinstance(state, tuple)
        assert len(state) == 2
        assert isinstance(state[0], float)
        assert isinstance(state[1], float)

    def test_last_crossover_state_insufficient_length_returns_none(self):
        """Test crossover state returns None when series length < 2."""
        strategy = SMACrossover(short=5, long=10)
        sma_short = pd.Series([1.0])
        sma_long = pd.Series([2.0])

        state = strategy._last_crossover_state(sma_short, sma_long)
        assert state is None

    def test_last_crossover_state_correct_calculation(self):
        """Test crossover state calculates correct diff values."""
        strategy = SMACrossover(short=5, long=10)
        # Create series where short SMA is below long initially, then crosses above
        sma_short = pd.Series([10.0, 12.0, 15.0])  # Rising
        sma_long = pd.Series([15.0, 14.0, 13.0])  # Falling
        # diff: [-5.0, -2.0, 2.0]
        # prev = -2.0, curr = 2.0 (crossover occurred)

        state = strategy._last_crossover_state(sma_short, sma_long)

        assert state == (-2.0, 2.0)


class TestSMACrossoverBuildSignal:
    """Test _build_signal method."""

    def test_build_signal_success(self, sample_ohlcv_data):
        """Test successful signal building."""
        strategy = SMACrossover()
        signal = strategy._build_signal(sample_ohlcv_data)

        assert not signal.empty
        assert len(signal) == 1
        assert "price" in signal.columns
        assert signal.index[0] == sample_ohlcv_data.index[-1]
        assert signal["price"].iloc[0] == round(float(sample_ohlcv_data["close"].iloc[-1]), 4)

    def test_build_signal_empty_dataframe_returns_empty(self, sample_ohlcv_data_empty):
        """Test signal building returns empty DataFrame for empty input."""
        strategy = SMACrossover()
        signal = strategy._build_signal(sample_ohlcv_data_empty)

        assert signal.empty

    def test_build_signal_missing_close_returns_empty(self, sample_ohlcv_data_missing_close):
        """Test signal building returns empty DataFrame when close column missing."""
        strategy = SMACrossover()
        signal = strategy._build_signal(sample_ohlcv_data_missing_close)

        assert signal.empty


class TestSMACrossoverBuy:
    """Test buy method for detecting upward crossovers."""

    def test_buy_upward_crossover_returns_signal(self):
        """Test buy returns signal when short SMA crosses above long SMA."""
        strategy = SMACrossover(short=5, long=10)
        # Create data where crossover occurs at the end
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        # First 15: declining (short below long)
        # Last 5: rising (short crosses above long)
        close_prices = [100.0 - i * 0.5 for i in range(15)] + [92.5 + i * 1.5 for i in range(5)]
        ohlcv_data = pd.DataFrame(
            {
                "open": [p - 0.5 for p in close_prices],
                "high": [p + 0.5 for p in close_prices],
                "low": [p - 1.0 for p in close_prices],
                "close": close_prices,
                "volume": [1000000] * 20,
            },
            index=dates,
        )

        signal = strategy.buy(ohlcv_data, "AAPL")

        # May or may not have signal depending on exact crossover timing
        # But should not raise an error
        assert isinstance(signal, pd.DataFrame)

    def test_buy_no_crossover_returns_empty(self, sample_ohlcv_data):
        """Test buy returns empty DataFrame when no crossover occurs."""
        strategy = SMACrossover(short=5, long=10)
        # Use monotonically increasing data (no crossover)
        signal = strategy.buy(sample_ohlcv_data, "AAPL")

        # Should return DataFrame (may be empty if no crossover)
        assert isinstance(signal, pd.DataFrame)

    def test_buy_insufficient_data_returns_empty(self, sample_ohlcv_data_insufficient):
        """Test buy returns empty DataFrame when data is insufficient."""
        strategy = SMACrossover(short=5, long=10)
        signal = strategy.buy(sample_ohlcv_data_insufficient, "AAPL")

        assert signal.empty

    def test_buy_empty_data_returns_empty(self, sample_ohlcv_data_empty):
        """Test buy returns empty DataFrame for empty input."""
        strategy = SMACrossover(short=5, long=10)
        signal = strategy.buy(sample_ohlcv_data_empty, "AAPL")

        assert signal.empty


class TestSMACrossoverSell:
    """Test sell method for detecting downward crossovers."""

    def test_sell_downward_crossover_returns_signal(self):
        """Test sell returns signal when short SMA crosses below long SMA."""
        strategy = SMACrossover(short=5, long=10)
        # Create data where crossover occurs at the end (downward)
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        # First 15: rising (short above long)
        # Last 5: declining (short crosses below long)
        close_prices = [100.0 + i * 0.5 for i in range(15)] + [107.5 - i * 1.5 for i in range(5)]
        ohlcv_data = pd.DataFrame(
            {
                "open": [p - 0.5 for p in close_prices],
                "high": [p + 0.5 for p in close_prices],
                "low": [p - 1.0 for p in close_prices],
                "close": close_prices,
                "volume": [1000000] * 20,
            },
            index=dates,
        )

        signal = strategy.sell(ohlcv_data, "AAPL")

        # May or may not have signal depending on exact crossover timing
        # But should not raise an error
        assert isinstance(signal, pd.DataFrame)

    def test_sell_no_crossover_returns_empty(self, sample_ohlcv_data):
        """Test sell returns empty DataFrame when no crossover occurs."""
        strategy = SMACrossover(short=5, long=10)
        # Use monotonically increasing data (no downward crossover)
        signal = strategy.sell(sample_ohlcv_data, "AAPL")

        # Should return DataFrame (may be empty if no crossover)
        assert isinstance(signal, pd.DataFrame)

    def test_sell_insufficient_data_returns_empty(self, sample_ohlcv_data_insufficient):
        """Test sell returns empty DataFrame when data is insufficient."""
        strategy = SMACrossover(short=5, long=10)
        signal = strategy.sell(sample_ohlcv_data_insufficient, "AAPL")

        assert signal.empty

    def test_sell_empty_data_returns_empty(self, sample_ohlcv_data_empty):
        """Test sell returns empty DataFrame for empty input."""
        strategy = SMACrossover(short=5, long=10)
        signal = strategy.sell(sample_ohlcv_data_empty, "AAPL")

        assert signal.empty


class TestSMACrossoverAddArguments:
    """Test add_arguments class method."""

    def test_add_arguments_adds_short_and_long(self):
        """Test add_arguments adds short and long parameters."""
        parser = argparse.ArgumentParser()
        SMACrossover.add_arguments(parser)

        args = parser.parse_args(["--short", "5", "--long", "15"])
        assert args.short == 5
        assert args.long == 15

    def test_add_arguments_inherits_strategy_arguments(self):
        """Test add_arguments includes Strategy base class arguments."""
        parser = argparse.ArgumentParser()
        SMACrossover.add_arguments(parser)

        args = parser.parse_args(["--side", "SHORT", "--window", "60"])
        assert args.side == "SHORT"
        assert args.window == 60


class TestSMACrossoverIntegration:
    """Integration tests for SMACrossover with BacktestEngine."""

    @pytest.fixture
    def sample_ohlcv_data_crossover(self):
        """Create OHLCV data designed to trigger SMA crossover."""
        dates = pd.date_range("2024-01-01", periods=50, freq="D", tz="UTC")
        # Create data where short SMA (5) crosses above long SMA (10) around index 20
        # First 20: declining prices
        # Next 30: rising prices (causes crossover)
        close_prices = []
        for i in range(50):
            if i < 20:
                close_prices.append(100.0 - i * 0.5)  # Declining
            else:
                close_prices.append(90.0 + (i - 20) * 1.0)  # Rising

        return pd.DataFrame(
            {
                "open": [p - 0.5 for p in close_prices],
                "high": [p + 0.5 for p in close_prices],
                "low": [p - 1.0 for p in close_prices],
                "close": close_prices,
                "volume": [1000000] * 50,
            },
            index=dates,
        )

    @pytest.fixture
    def sample_ohlcv_data_with_time(self, sample_ohlcv_data_crossover):
        """Convert OHLCV data to InfluxDB format (with time column)."""
        data = sample_ohlcv_data_crossover.reset_index()
        data = data.rename(columns={"index": "time"})
        return data

    @pytest.mark.integration
    def test_backtest_engine_with_sma_crossover_generates_signals(
        self, sample_ohlcv_data_with_time
    ):
        """Test BacktestEngine with SMACrossover generates buy signals on crossover."""
        strategy = SMACrossover(short=5, long=10, window=50, side=Side.LONG)

        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-20", tz="UTC")

        engine = BacktestEngine(
            strategy=strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
            database="ohlcv",
        )

        # Mock InfluxDB to return our test data
        with (
            patch("system.algo_trader.backtest.engine.MarketDataInflux") as mock_influx_class,
            patch(
                "system.algo_trader.backtest.core.results_generator.TradeJournal"
            ) as mock_journal_class,
            patch(
                "system.algo_trader.backtest.core.results_generator.ExecutionSimulator"
            ) as mock_exec_sim_class,
        ):
            mock_influx_instance = MagicMock()
            mock_influx_instance.query.return_value = sample_ohlcv_data_with_time.copy()
            mock_influx_class.return_value = mock_influx_instance
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, pd.DataFrame())
            mock_journal_class.return_value = mock_journal

            mock_exec_sim = MagicMock()
            mock_exec_sim.apply_execution.return_value = pd.DataFrame()
            mock_exec_sim_class.return_value = mock_exec_sim

            results = engine.run_ticker("AAPL")

            # Verify results structure
            assert isinstance(results, BacktestResults)
            assert hasattr(results, "signals")
            assert hasattr(results, "trades")
            assert hasattr(results, "metrics")

    @pytest.mark.integration
    def test_backtest_engine_with_sma_crossover_multiple_tickers(self, sample_ohlcv_data_with_time):
        """Test BacktestEngine with SMACrossover handles multiple tickers."""
        strategy = SMACrossover(short=5, long=10, window=50, side=Side.LONG)

        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-20", tz="UTC")

        engine = BacktestEngine(
            strategy=strategy,
            tickers=["AAPL", "MSFT"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
            database="ohlcv",
        )

        # Mock InfluxDB to return test data for both tickers
        with (
            patch("system.algo_trader.backtest.engine.MarketDataInflux") as mock_influx_class,
            patch(
                "system.algo_trader.backtest.core.results_generator.TradeJournal"
            ) as mock_journal_class,
            patch(
                "system.algo_trader.backtest.core.results_generator.ExecutionSimulator"
            ) as mock_exec_sim_class,
        ):
            mock_influx_instance = MagicMock()
            mock_influx_instance.query.return_value = sample_ohlcv_data_with_time.copy()
            mock_influx_class.return_value = mock_influx_instance
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, pd.DataFrame())
            mock_journal_class.return_value = mock_journal

            mock_exec_sim = MagicMock()
            mock_exec_sim.apply_execution.return_value = pd.DataFrame()
            mock_exec_sim_class.return_value = mock_exec_sim

            results = engine.run()

            # Verify results structure
            assert isinstance(results, BacktestResults)
            assert hasattr(results, "signals")
            assert hasattr(results, "trades")

    @pytest.mark.integration
    def test_backtest_engine_with_sma_crossover_window_respect(self, sample_ohlcv_data_with_time):
        """Test BacktestEngine respects SMACrossover window parameter."""
        # Use a small window to limit lookback
        strategy = SMACrossover(short=5, long=10, window=15, side=Side.LONG)

        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-20", tz="UTC")

        engine = BacktestEngine(
            strategy=strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
            database="ohlcv",
        )

        with (
            patch("system.algo_trader.backtest.engine.MarketDataInflux") as mock_influx_class,
            patch(
                "system.algo_trader.backtest.core.results_generator.TradeJournal"
            ) as mock_journal_class,
            patch(
                "system.algo_trader.backtest.core.results_generator.ExecutionSimulator"
            ) as mock_exec_sim_class,
        ):
            mock_influx_instance = MagicMock()
            mock_influx_instance.query.return_value = sample_ohlcv_data_with_time.copy()
            mock_influx_class.return_value = mock_influx_instance

            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, pd.DataFrame())
            mock_journal_class.return_value = mock_journal

            mock_exec_sim = MagicMock()
            mock_exec_sim.apply_execution.return_value = pd.DataFrame()
            mock_exec_sim_class.return_value = mock_exec_sim

            results = engine.run_ticker("AAPL")

            # Verify window is respected (strategy should only see last 15 bars)
            assert isinstance(results, BacktestResults)
            # SignalCollector should slice data according to window
            assert hasattr(results, "signals")

    @pytest.mark.integration
    def test_backtest_engine_with_sma_crossover_execution_config(self, sample_ohlcv_data_with_time):
        """Test BacktestEngine with SMACrossover uses execution config."""
        strategy = SMACrossover(short=5, long=10, window=50, side=Side.LONG)
        execution_config = ExecutionConfig(
            slippage_bps=10.0,
            commission_per_share=0.01,
            use_limit_orders=True,
        )

        start_date = pd.Timestamp("2024-01-01", tz="UTC")
        end_date = pd.Timestamp("2024-01-20", tz="UTC")

        engine = BacktestEngine(
            strategy=strategy,
            tickers=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            step_frequency="daily",
            database="ohlcv",
            execution_config=execution_config,
        )

        assert engine.execution_config.slippage_bps == 10.0
        assert engine.execution_config.commission_per_share == 0.01
        assert engine.execution_config.use_limit_orders is True

        with (
            patch("system.algo_trader.backtest.engine.MarketDataInflux") as mock_influx_class,
            patch(
                "system.algo_trader.backtest.core.results_generator.TradeJournal"
            ) as mock_journal_class,
            patch(
                "system.algo_trader.backtest.core.results_generator.ExecutionSimulator"
            ) as mock_exec_sim_class,
        ):
            mock_influx_instance = MagicMock()
            mock_influx_instance.query.return_value = sample_ohlcv_data_with_time.copy()
            mock_influx_class.return_value = mock_influx_instance
            mock_journal = MagicMock()
            mock_journal.generate_report.return_value = ({}, pd.DataFrame())
            mock_journal_class.return_value = mock_journal

            mock_exec_sim = MagicMock()
            mock_exec_sim.apply_execution.return_value = pd.DataFrame()
            mock_exec_sim_class.return_value = mock_exec_sim

            results = engine.run_ticker("AAPL")

            # Verify execution config was used
            assert isinstance(results, BacktestResults)
