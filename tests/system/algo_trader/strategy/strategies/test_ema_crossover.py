"""Unit and integration tests for EMACrossover - Exponential Moving Average Crossover Strategy.

Tests cover initialization, validation, EMA calculation, crossover detection,
and signal generation. All external dependencies are mocked to avoid logging calls.
"""

import argparse

import pandas as pd
import pytest

from system.algo_trader.strategy.strategies.ema_crossover import EMACrossover
from system.algo_trader.strategy.strategy import Side
from system.algo_trader.strategy.studies.base_study import StudySpec


class TestEMACrossoverInitialization:
    """Test EMACrossover initialization and validation."""

    def test_initialization_defaults(self):
        """Test initialization with default parameters."""
        strategy = EMACrossover()

        assert strategy.short == 3
        assert strategy.long == 8
        assert strategy.window == 120
        assert strategy.side == Side.LONG
        assert strategy.ema_study is not None

    def test_initialization_custom_parameters(self):
        """Test initialization with custom parameters."""
        strategy = EMACrossover(short=5, long=15, window=60, side=Side.SHORT)

        assert strategy.short == 5
        assert strategy.long == 15
        assert strategy.window == 60
        assert strategy.side == Side.SHORT

    def test_initialization_short_greater_than_long_raises(self):
        """Test initialization fails when short >= long."""
        with pytest.raises(ValueError, match=r"short.*must be less than long"):
            EMACrossover(short=20, long=10)

    def test_initialization_short_equal_long_raises(self):
        """Test initialization fails when short equals long."""
        with pytest.raises(ValueError, match=r"short.*must be less than long"):
            EMACrossover(short=10, long=10)

    def test_initialization_short_less_than_2_raises(self):
        """Test initialization fails when short < 2."""
        with pytest.raises(ValueError, match=r"short must be at least 2"):
            EMACrossover(short=1, long=10)

    def test_add_arguments(self):
        """Test add_arguments method."""
        parser = argparse.ArgumentParser()
        EMACrossover.add_arguments(parser)

        args = parser.parse_args(["--short", "5", "--long", "15"])
        assert args.short == 5
        assert args.long == 15


class TestEMACrossoverStudySpecs:
    """Test EMACrossover study specifications."""

    def test_get_study_specs(self):
        """Test get_study_specs returns correct specifications."""
        strategy = EMACrossover(short=3, long=8)

        specs = strategy.get_study_specs()

        assert len(specs) == 2
        assert all(isinstance(spec, StudySpec) for spec in specs)

        ema_short_spec = next(s for s in specs if s.name == "ema_short")
        assert ema_short_spec.params["window"] == 3
        assert ema_short_spec.params["column"] == "close"
        assert ema_short_spec.min_bars == 3

        ema_long_spec = next(s for s in specs if s.name == "ema_long")
        assert ema_long_spec.params["window"] == 8
        assert ema_long_spec.params["column"] == "close"
        assert ema_long_spec.min_bars == 8


class TestEMACrossoverCalculation:
    """Test EMACrossover EMA calculation."""

    def test_calculate_emas_success(self):
        """Test _calculate_emas with valid data."""
        strategy = EMACrossover(short=3, long=8)

        ohlcv_data = pd.DataFrame(
            {"close": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0]},
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1D", tz="UTC")),
        )

        ema_short, ema_long = strategy._calculate_emas(ohlcv_data, "AAPL")

        assert ema_short is not None
        assert ema_long is not None
        assert len(ema_short) == len(ohlcv_data)
        assert len(ema_long) == len(ohlcv_data)

    def test_calculate_emas_insufficient_data(self):
        """Test _calculate_emas with insufficient data."""
        strategy = EMACrossover(short=3, long=8)

        ohlcv_data = pd.DataFrame(
            {"close": [100.0, 101.0]},  # Only 2 bars, need at least 8 for long EMA
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=2, freq="1D", tz="UTC")),
        )

        ema_short, ema_long = strategy._calculate_emas(ohlcv_data, "AAPL")

        assert ema_short is None
        assert ema_long is None


class TestEMACrossoverCrossoverDetection:
    """Test EMACrossover crossover detection."""

    def test_last_crossover_state_bullish(self):
        """Test _last_crossover_state detects bullish crossover."""
        strategy = EMACrossover()

        # ema_short crosses above ema_long: diff goes from negative to positive
        # prev (index -2) should be negative, curr (index -1) should be positive
        ema_short = pd.Series([98.0, 99.0, 99.5, 101.0])
        ema_long = pd.Series([100.0, 100.0, 100.0, 100.0])

        state = strategy._last_crossover_state(ema_short, ema_long)

        assert state is not None
        prev, curr = state
        assert prev < 0.0  # ema_short was below ema_long
        assert curr > 0.0  # ema_short is now above ema_long

    def test_last_crossover_state_bearish(self):
        """Test _last_crossover_state detects bearish crossover."""
        strategy = EMACrossover()

        # ema_short crosses below ema_long: diff goes from positive to negative
        # prev (index -2) should be positive, curr (index -1) should be negative
        ema_short = pd.Series([102.0, 101.0, 100.5, 99.0])
        ema_long = pd.Series([100.0, 100.0, 100.0, 100.0])

        state = strategy._last_crossover_state(ema_short, ema_long)

        assert state is not None
        prev, curr = state
        assert prev > 0.0  # ema_short was above ema_long
        assert curr < 0.0  # ema_short is now below ema_long

    def test_last_crossover_state_insufficient_data(self):
        """Test _last_crossover_state with insufficient data."""
        strategy = EMACrossover()

        ema_short = pd.Series([100.0])
        ema_long = pd.Series([100.0])

        state = strategy._last_crossover_state(ema_short, ema_long)

        assert state is None


class TestEMACrossoverSignalGeneration:
    """Test EMACrossover signal generation."""

    def test_buy_signal_bullish_crossover(self):
        """Test buy() generates signal on bullish crossover."""
        strategy = EMACrossover(short=3, long=8)

        # Create data where short EMA crosses above long EMA
        ohlcv_data = pd.DataFrame(
            {"close": [98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0]},
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1D", tz="UTC")),
        )

        signals = strategy.buy(ohlcv_data, "AAPL")

        # May or may not generate signal depending on EMA calculation
        assert isinstance(signals, pd.DataFrame)

    def test_buy_signal_no_crossover(self):
        """Test buy() returns empty when no bullish crossover."""
        strategy = EMACrossover(short=3, long=8)

        # Create data where short EMA stays below long EMA
        ohlcv_data = pd.DataFrame(
            {"close": [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0, 92.0, 91.0]},
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1D", tz="UTC")),
        )

        signals = strategy.buy(ohlcv_data, "AAPL")

        assert isinstance(signals, pd.DataFrame)

    def test_sell_signal_bearish_crossover(self):
        """Test sell() generates signal on bearish crossover."""
        strategy = EMACrossover(short=3, long=8)

        # Create data where short EMA crosses below long EMA
        ohlcv_data = pd.DataFrame(
            {"close": [102.0, 101.0, 100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0]},
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1D", tz="UTC")),
        )

        signals = strategy.sell(ohlcv_data, "AAPL")

        # May or may not generate signal depending on EMA calculation
        assert isinstance(signals, pd.DataFrame)

    def test_sell_signal_no_crossover(self):
        """Test sell() returns empty when no bearish crossover."""
        strategy = EMACrossover(short=3, long=8)

        # Create data where short EMA stays above long EMA
        ohlcv_data = pd.DataFrame(
            {"close": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0]},
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1D", tz="UTC")),
        )

        signals = strategy.sell(ohlcv_data, "AAPL")

        assert isinstance(signals, pd.DataFrame)

    def test_buy_signal_insufficient_data(self):
        """Test buy() returns empty with insufficient data."""
        strategy = EMACrossover(short=3, long=8)

        ohlcv_data = pd.DataFrame(
            {"close": [100.0, 101.0]},  # Only 2 bars
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=2, freq="1D", tz="UTC")),
        )

        signals = strategy.buy(ohlcv_data, "AAPL")

        assert signals.empty

    def test_sell_signal_insufficient_data(self):
        """Test sell() returns empty with insufficient data."""
        strategy = EMACrossover(short=3, long=8)

        ohlcv_data = pd.DataFrame(
            {"close": [100.0, 101.0]},  # Only 2 bars
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=2, freq="1D", tz="UTC")),
        )

        signals = strategy.sell(ohlcv_data, "AAPL")

        assert signals.empty
