"""Unit tests for Strategy - Base Strategy Interface.

Tests cover initialization, argument parsing, study specs, and signal building.
All external dependencies are mocked via conftest.py.
"""

import argparse
from unittest.mock import MagicMock

import pandas as pd
import pytest

from system.algo_trader.strategy.strategy import Side, Strategy


class ConcreteStrategy(Strategy):
    """Concrete implementation of Strategy for testing."""

    def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate buy signals."""
        return pd.DataFrame()

    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate sell signals."""
        return pd.DataFrame()


class TestStrategyInitialization:
    """Test Strategy initialization."""

    def test_initialization_defaults(self):
        """Test initialization with default parameters."""
        strategy = ConcreteStrategy()

        assert strategy.side == Side.LONG
        assert strategy.window is None
        assert strategy.strategy_name == "ConcreteStrategy"

    def test_initialization_custom_side(self):
        """Test initialization with custom side."""
        strategy = ConcreteStrategy(side=Side.SHORT)

        assert strategy.side == Side.SHORT

    def test_initialization_custom_window(self):
        """Test initialization with custom window."""
        strategy = ConcreteStrategy(window=60)

        assert strategy.window == 60

    def test_initialization_extra_kwargs_ignored(self):
        """Test initialization ignores extra keyword arguments."""
        strategy = ConcreteStrategy(extra_param="ignored", another_param=123)

        assert not hasattr(strategy, "extra_param")
        assert not hasattr(strategy, "another_param")


class TestStrategyAddArguments:
    """Test Strategy add_arguments method."""

    def test_add_arguments_defaults(self):
        """Test add_arguments adds default arguments."""
        parser = argparse.ArgumentParser()
        Strategy.add_arguments(parser)

        args = parser.parse_args([])

        assert args.side == "LONG"
        assert args.window is None

    def test_add_arguments_custom_side(self):
        """Test add_arguments with custom side."""
        parser = argparse.ArgumentParser()
        Strategy.add_arguments(parser)

        args = parser.parse_args(["--side", "SHORT"])

        assert args.side == "SHORT"

    def test_add_arguments_custom_window(self):
        """Test add_arguments with custom window."""
        parser = argparse.ArgumentParser()
        Strategy.add_arguments(parser)

        args = parser.parse_args(["--window", "60"])

        assert args.window == 60

    def test_add_arguments_invalid_side(self):
        """Test add_arguments with invalid side."""
        parser = argparse.ArgumentParser()
        Strategy.add_arguments(parser)

        with pytest.raises(SystemExit):
            parser.parse_args(["--side", "INVALID"])


class TestStrategyGetStudySpecs:
    """Test Strategy get_study_specs method."""

    def test_get_study_specs_default(self):
        """Test get_study_specs returns empty list by default."""
        strategy = ConcreteStrategy()

        specs = strategy.get_study_specs()

        assert isinstance(specs, list)
        assert len(specs) == 0


class TestStrategyBuildPriceSignal:
    """Test Strategy _build_price_signal method."""

    def test_build_price_signal_success(self):
        """Test _build_price_signal with valid data."""
        strategy = ConcreteStrategy()

        ohlcv_data = pd.DataFrame(
            {"close": [100.0, 101.0, 102.0]},
            index=pd.DatetimeIndex(
                pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC")
            ),
        )

        signal = strategy._build_price_signal(ohlcv_data)

        assert not signal.empty
        assert "price" in signal.columns
        assert len(signal) == 1
        assert signal["price"].iloc[0] == 102.0

    def test_build_price_signal_empty_data(self):
        """Test _build_price_signal with empty data."""
        strategy = ConcreteStrategy()

        ohlcv_data = pd.DataFrame()

        signal = strategy._build_price_signal(ohlcv_data)

        assert signal.empty

    def test_build_price_signal_none(self):
        """Test _build_price_signal with None."""
        strategy = ConcreteStrategy()

        signal = strategy._build_price_signal(None)

        assert signal.empty

    def test_build_price_signal_missing_close(self):
        """Test _build_price_signal with missing close column."""
        strategy = ConcreteStrategy()

        ohlcv_data = pd.DataFrame(
            {"open": [100.0, 101.0, 102.0]},
            index=pd.DatetimeIndex(
                pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC")
            ),
        )

        signal = strategy._build_price_signal(ohlcv_data)

        assert signal.empty

    def test_build_price_signal_rounds_price(self):
        """Test _build_price_signal rounds price to 4 decimal places."""
        strategy = ConcreteStrategy()

        ohlcv_data = pd.DataFrame(
            {"close": [100.123456789]},
            index=pd.DatetimeIndex(["2024-01-01"], tz="UTC"),
        )

        signal = strategy._build_price_signal(ohlcv_data)

        assert signal["price"].iloc[0] == 100.1235  # Rounded to 4 decimals


class TestSideEnum:
    """Test Side enumeration."""

    def test_side_long(self):
        """Test Side.LONG value."""
        assert Side.LONG == "LONG"

    def test_side_short(self):
        """Test Side.SHORT value."""
        assert Side.SHORT == "SHORT"

    def test_side_enum_values(self):
        """Test Side enum has correct values."""
        assert Side.LONG.value == "LONG"
        assert Side.SHORT.value == "SHORT"

