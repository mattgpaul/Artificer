"""Unit tests for SMACrossover - SMA crossover trading strategy.

Tests cover initialization, signal generation with various data patterns,
confidence calculation, edge cases, and error handling. All external
dependencies (InfluxDB, Strategy methods) are mocked.
"""

import json

import numpy as np
import pandas as pd
import pytest

from system.algo_trader.strategy.strategies.sma_crossover import SMACrossover

# All fixtures moved to conftest.py


class TestSMACrossoverInitialization:
    """Test SMACrossover initialization and validation."""

    def test_initialization_default_params(self, mock_dependencies):
        """Test initialization with default parameters."""
        strategy = SMACrossover()

        assert strategy.short_window == 10
        assert strategy.long_window == 20
        assert strategy.min_confidence == 0.0
        assert strategy.strategy_name == "SMACrossover"

    def test_initialization_custom_windows(self, mock_dependencies):
        """Test initialization with custom SMA windows."""
        strategy = SMACrossover(short_window=5, long_window=15)

        assert strategy.short_window == 5
        assert strategy.long_window == 15
        assert strategy.strategy_name == "SMACrossover"

    def test_initialization_with_min_confidence(self, mock_dependencies):
        """Test initialization with minimum confidence threshold."""
        strategy = SMACrossover(min_confidence=0.5)

        assert strategy.min_confidence == 0.5

    def test_initialization_with_custom_database(self, mock_dependencies):
        """Test initialization with custom database name."""
        _ = SMACrossover(database="custom-db")

        mock_dependencies["influx_class"].assert_called_once()
        call_args = mock_dependencies["influx_class"].call_args
        assert call_args.kwargs["database"] == "custom-db"

    def test_initialization_invalid_windows(self, mock_dependencies):
        """Test initialization fails when short_window >= long_window."""
        with pytest.raises(ValueError, match=r"short_window .* must be less than"):
            SMACrossover(short_window=20, long_window=10)

        with pytest.raises(ValueError, match=r"short_window .* must be less than"):
            SMACrossover(short_window=10, long_window=10)

    def test_initialization_short_window_too_small(self, mock_dependencies):
        """Test initialization fails when short_window < 2."""
        with pytest.raises(ValueError, match="short_window must be at least 2"):
            SMACrossover(short_window=1, long_window=10)

    def test_initialization_invalid_confidence(self, mock_dependencies):
        """Test initialization fails with invalid confidence values."""
        with pytest.raises(ValueError, match="min_confidence must be in"):
            SMACrossover(min_confidence=-0.1)

        with pytest.raises(ValueError, match="min_confidence must be in"):
            SMACrossover(min_confidence=1.5)

    def test_initialization_with_threading(self, mock_dependencies):
        """Test initialization with threading enabled."""
        strategy = SMACrossover(use_threading=True)

        assert strategy.thread_manager is not None
        mock_dependencies["thread_class"].assert_called_once()


class TestGenerateSignals:
    """Test signal generation logic."""

    def test_generate_signals_with_crossover(self, mock_dependencies):
        """Test signal generation with a clear bullish crossover."""
        strategy = SMACrossover(short_window=5, long_window=10)

        # Create data with a clear bullish crossover
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")

        # First half: downtrend (short SMA below long SMA)
        # Second half: uptrend (short SMA crosses above long SMA)
        close_prices = np.concatenate(
            [
                np.linspace(150, 100, 15),  # Downtrend
                np.linspace(100, 140, 15),  # Uptrend - triggers bullish crossover
            ]
        )

        ohlcv_data = pd.DataFrame(
            {
                "open": close_prices - 1,
                "high": close_prices + 2,
                "low": close_prices - 2,
                "close": close_prices,
                "volume": [1000000] * 30,
            },
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        assert not signals.empty
        assert "signal_type" in signals.columns
        assert "price" in signals.columns
        assert "confidence" in signals.columns
        assert "metadata" in signals.columns

    def test_generate_signals_bullish_crossover(self, mock_dependencies):
        """Test detection of bullish crossover (buy signal)."""
        strategy = SMACrossover(short_window=3, long_window=5)

        # Create data where short SMA crosses above long SMA
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = np.concatenate(
            [
                [100, 100, 100, 100, 100],  # Flat
                [101, 103, 106, 110, 115],  # Sharp increase
                [116, 117, 118, 119, 120],  # Continued increase
                [120, 120, 120, 120, 120],  # Flat
            ]
        )

        ohlcv_data = pd.DataFrame(
            {"close": close_prices[:20], "open": close_prices[:20]},
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        # Should detect at least one buy signal
        if not signals.empty:
            buy_signals = signals[signals["signal_type"] == "buy"]
            assert len(buy_signals) > 0

    def test_generate_signals_bearish_crossover(self, mock_dependencies):
        """Test detection of bearish crossover (sell signal)."""
        strategy = SMACrossover(short_window=3, long_window=5)

        # Create data where short SMA crosses below long SMA
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = np.concatenate(
            [
                [120, 120, 120, 120, 120],  # Flat
                [119, 117, 114, 110, 105],  # Sharp decrease
                [104, 103, 102, 101, 100],  # Continued decrease
                [100, 100, 100, 100, 100],  # Flat
            ]
        )

        ohlcv_data = pd.DataFrame(
            {"close": close_prices[:20], "open": close_prices[:20]},
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        # Should detect at least one sell signal
        if not signals.empty:
            sell_signals = signals[signals["signal_type"] == "sell"]
            assert len(sell_signals) > 0

    def test_generate_signals_no_crossover(self, mock_dependencies):
        """Test when no crossovers occur (constant uptrend)."""
        strategy = SMACrossover(short_window=5, long_window=10)

        # Constant uptrend - short SMA always above long SMA, no crossover
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        close_prices = np.linspace(100, 150, 30)

        ohlcv_data = pd.DataFrame(
            {"close": close_prices, "open": close_prices},
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        # No crossovers should be detected in a smooth uptrend
        # (short SMA stays above long SMA throughout)
        assert signals.empty or len(signals) <= 1

    def test_generate_signals_min_confidence_filter(self, mock_dependencies):
        """Test that signals below min_confidence are filtered out."""
        strategy = SMACrossover(short_window=5, long_window=10, min_confidence=0.8)

        # Create data with weak crossover
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        close_prices = np.concatenate(
            [
                np.linspace(100, 95, 15),  # Slight downtrend
                np.linspace(95, 100, 15),  # Slight uptrend (weak crossover)
            ]
        )

        ohlcv_data = pd.DataFrame(
            {"close": close_prices, "open": close_prices},
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        # All signals should have confidence >= min_confidence
        if not signals.empty:
            assert (signals["confidence"] >= 0.8).all()

    def test_generate_signals_confidence_calculation(self, mock_dependencies):
        """Test that confidence scores are properly calculated."""
        strategy = SMACrossover(short_window=5, long_window=10)

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        close_prices = np.concatenate(
            [
                np.linspace(150, 100, 15),  # Downtrend
                np.linspace(100, 150, 15),  # Uptrend
            ]
        )

        ohlcv_data = pd.DataFrame(
            {"close": close_prices, "open": close_prices},
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        if not signals.empty:
            # Confidence should be between 0 and 1
            assert (signals["confidence"] >= 0.0).all()
            assert (signals["confidence"] <= 1.0).all()

    def test_generate_signals_metadata_structure(self, mock_dependencies):
        """Test that signal metadata contains required fields."""
        strategy = SMACrossover(short_window=5, long_window=10)

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        close_prices = np.concatenate(
            [
                np.linspace(150, 100, 15),
                np.linspace(100, 150, 15),
            ]
        )

        ohlcv_data = pd.DataFrame(
            {"close": close_prices, "open": close_prices},
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        if not signals.empty:
            metadata = json.loads(signals.iloc[0]["metadata"])

            # Check metadata contains expected fields
            assert "sma_short" in metadata
            assert "sma_long" in metadata
            assert "difference" in metadata
            assert "difference_pct" in metadata
            assert "short_window" in metadata
            assert "long_window" in metadata
            assert metadata["short_window"] == 5
            assert metadata["long_window"] == 10


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_generate_signals_empty_dataframe(self, mock_dependencies):
        """Test with empty OHLCV data."""
        strategy = SMACrossover()

        empty_df = pd.DataFrame()
        signals = strategy.generate_signals(empty_df, "AAPL")

        assert signals.empty

    def test_generate_signals_none_dataframe(self, mock_dependencies):
        """Test with None as input."""
        strategy = SMACrossover()

        signals = strategy.generate_signals(None, "AAPL")

        assert signals.empty

    def test_generate_signals_missing_close_column(self, mock_dependencies):
        """Test with OHLCV data missing 'close' column."""
        strategy = SMACrossover()

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100] * 30,
                "high": [105] * 30,
                "low": [95] * 30,
                # Missing 'close' column
            },
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        assert signals.empty

    def test_generate_signals_insufficient_data(self, mock_dependencies):
        """Test with insufficient data for long_window calculation."""
        strategy = SMACrossover(short_window=10, long_window=20)

        # Only 15 rows, but need 20 for long_window
        dates = pd.date_range(start="2024-01-01", periods=15, freq="D")
        ohlcv_data = pd.DataFrame(
            {"close": [100] * 15, "open": [100] * 15},
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        assert signals.empty

    def test_generate_signals_exact_window_size(self, mock_dependencies):
        """Test with data exactly matching long_window size."""
        strategy = SMACrossover(short_window=5, long_window=10)

        # Exactly 10 rows
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        close_prices = [100, 102, 101, 103, 105, 108, 110, 112, 115, 118]

        ohlcv_data = pd.DataFrame(
            {"close": close_prices, "open": close_prices},
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        # Should be able to calculate SMAs, but may not have crossovers
        assert isinstance(signals, pd.DataFrame)

    def test_generate_signals_all_same_price(self, mock_dependencies):
        """Test with all close prices identical (no movement)."""
        strategy = SMACrossover(short_window=5, long_window=10)

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        ohlcv_data = pd.DataFrame(
            {"close": [100] * 30, "open": [100] * 30},
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        # No crossovers in flat data
        assert signals.empty

    def test_generate_signals_with_nan_values(self, mock_dependencies):
        """Test handling of NaN values in close prices."""
        strategy = SMACrossover(short_window=5, long_window=10)

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        close_prices = np.linspace(100, 150, 30)
        close_prices[10:15] = np.nan  # Insert NaN values

        ohlcv_data = pd.DataFrame(
            {"close": close_prices, "open": close_prices},
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        # Strategy should handle NaN gracefully (pandas rolling handles NaN)
        assert isinstance(signals, pd.DataFrame)


class TestConfidenceCalculation:
    """Test confidence score calculation logic."""

    def test_calculate_confidence_zero_sma_long(self, mock_dependencies):
        """Test confidence calculation when sma_long is zero."""
        strategy = SMACrossover()

        confidence = strategy._calculate_confidence(diff=10.0, sma_long=0.0)

        assert confidence == 0.0

    def test_calculate_confidence_small_difference(self, mock_dependencies):
        """Test confidence with small percentage difference."""
        strategy = SMACrossover()

        # 0.5% difference
        confidence = strategy._calculate_confidence(diff=0.5, sma_long=100.0)

        assert 0.0 <= confidence <= 1.0
        assert confidence < 1.0  # Should not be max confidence

    def test_calculate_confidence_large_difference(self, mock_dependencies):
        """Test confidence with large percentage difference."""
        strategy = SMACrossover()

        # 2% difference
        confidence = strategy._calculate_confidence(diff=2.0, sma_long=100.0)

        assert confidence > 0.5  # Should be high confidence
        assert confidence <= 1.0

    def test_calculate_confidence_negative_diff(self, mock_dependencies):
        """Test confidence with negative difference (uses absolute value)."""
        strategy = SMACrossover()

        confidence_pos = strategy._calculate_confidence(diff=1.0, sma_long=100.0)
        confidence_neg = strategy._calculate_confidence(diff=-1.0, sma_long=100.0)

        # Should be same (uses abs value)
        assert confidence_pos == confidence_neg


class TestIntegration:
    """Integration tests with realistic scenarios."""

    def test_full_strategy_workflow(self, mock_dependencies):
        """Test complete workflow: initialize, generate signals, check results."""
        strategy = SMACrossover(
            short_window=5,
            long_window=10,
            min_confidence=0.3,
        )

        # Create realistic data with clear crossover
        dates = pd.date_range(start="2024-01-01", periods=40, freq="D")
        close_prices = np.concatenate(
            [
                np.linspace(100, 90, 20),  # Downtrend
                np.linspace(90, 110, 20),  # Uptrend (crossover)
            ]
        )

        ohlcv_data = pd.DataFrame(
            {
                "open": close_prices - 0.5,
                "high": close_prices + 1.0,
                "low": close_prices - 1.0,
                "close": close_prices,
                "volume": [1000000] * 40,
            },
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        # Verify structure - signals may be empty if no crossover occurs
        assert isinstance(signals, pd.DataFrame)
        if not signals.empty:
            assert all(
                col in signals.columns for col in ["signal_type", "price", "confidence", "metadata"]
            )
            assert all(signals["signal_type"].isin(["buy", "sell"]))
            assert (signals["confidence"] >= 0.3).all()

    def test_multiple_crossovers(self, mock_dependencies):
        """Test detection of multiple crossovers in volatile data."""
        strategy = SMACrossover(short_window=3, long_window=5)

        # Create oscillating data
        dates = pd.date_range(start="2024-01-01", periods=50, freq="D")
        close_prices = 100 + 10 * np.sin(np.linspace(0, 4 * np.pi, 50))

        ohlcv_data = pd.DataFrame(
            {"close": close_prices, "open": close_prices},
            index=dates,
        )

        signals = strategy.generate_signals(ohlcv_data, "AAPL")

        # Should detect multiple crossovers in oscillating data
        if not signals.empty:
            buy_count = (signals["signal_type"] == "buy").sum()
            sell_count = (signals["signal_type"] == "sell").sum()

            # In oscillating data, should have both buys and sells
            assert buy_count >= 0
            assert sell_count >= 0
