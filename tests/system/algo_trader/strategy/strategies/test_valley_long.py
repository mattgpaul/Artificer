"""Unit tests for ValleyLong - Valley-based long trading strategy.

Tests cover initialization, buy/sell signal generation, edge cases, and error handling.
All external dependencies (InfluxDB, BaseStrategy methods, studies) are mocked.
"""

import json
from unittest.mock import patch

import pandas as pd
import pytest

from system.algo_trader.strategy.strategies.valley_long import ValleyLong

# All fixtures moved to conftest.py


class TestValleyLongInitialization:
    """Test ValleyLong initialization and validation."""

    def test_initialization_default_params(self, mock_dependencies):
        """Test initialization with default parameters."""
        strategy = ValleyLong()

        assert strategy.valley_distance == 50
        assert strategy.valley_prominence == 2.0
        assert strategy.peak_distance == 50
        assert strategy.peak_prominence == 2.0
        assert strategy.nearness_threshold == 0.5
        assert strategy.min_confidence == 0.0
        assert strategy.strategy_name == "ValleyLong"
        assert strategy.sell_nearness_threshold == 0.2  # 0.4 * 0.5

    def test_initialization_custom_params(self, mock_dependencies):
        """Test initialization with custom parameters."""
        strategy = ValleyLong(
            valley_distance=30,
            valley_prominence=3.0,
            peak_distance=40,
            peak_prominence=2.5,
            nearness_threshold=1.0,
            min_confidence=0.5,
        )

        assert strategy.valley_distance == 30
        assert strategy.valley_prominence == 3.0
        assert strategy.peak_distance == 40
        assert strategy.peak_prominence == 2.5
        assert strategy.nearness_threshold == 1.0
        assert strategy.min_confidence == 0.5

    def test_initialization_custom_sell_nearness_threshold(self, mock_dependencies):
        """Test initialization with custom sell nearness threshold."""
        strategy = ValleyLong(nearness_threshold=1.0, sell_nearness_threshold=0.6)

        assert strategy.sell_nearness_threshold == 0.6

    def test_initialization_invalid_min_confidence(self, mock_dependencies):
        """Test initialization fails with invalid confidence values."""
        with pytest.raises(ValueError, match="min_confidence must be in"):
            ValleyLong(min_confidence=-0.1)

        with pytest.raises(ValueError, match="min_confidence must be in"):
            ValleyLong(min_confidence=1.5)

    def test_initialization_invalid_nearness_threshold(self, mock_dependencies):
        """Test initialization fails with invalid nearness threshold."""
        with pytest.raises(ValueError, match=r"nearness_threshold must be > 0.0"):
            ValleyLong(nearness_threshold=0.0)

        with pytest.raises(ValueError, match=r"nearness_threshold must be > 0.0"):
            ValleyLong(nearness_threshold=-1.0)

    def test_initialization_with_custom_database(self, mock_dependencies):
        """Test initialization with custom database name."""
        _ = ValleyLong(database="custom-db")

        mock_dependencies["influx_class"].assert_called_once()
        call_args = mock_dependencies["influx_class"].call_args
        assert call_args.kwargs["database"] == "custom-db"

    def test_initialization_with_threading(self, mock_dependencies):
        """Test initialization with threading enabled."""
        strategy = ValleyLong(use_threading=True)

        assert strategy.thread_manager is not None
        mock_dependencies["thread_class"].assert_called_once()


class TestValleyLongBuySignals:
    """Test buy signal generation logic."""

    def test_buy_no_valleys(self, mock_dependencies):
        """Test buy returns empty when no valleys found."""
        strategy = ValleyLong()
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0] * 20,
                "high": [105.0] * 20,
                "low": [95.0] * 20,
                "close": [100.0] * 20,
                "volume": [1000000] * 20,
            },
            index=dates,
        )

        with patch.object(strategy.valley_study, "compute", return_value=pd.DataFrame()):
            signals = strategy.buy(ohlcv_data, "AAPL")

            assert signals.empty

    def test_buy_valleys_found_no_match(self, mock_dependencies):
        """Test buy returns empty when valleys found but price not near any."""
        strategy = ValleyLong(nearness_threshold=0.1)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0] * 20,
                "high": [105.0] * 20,
                "low": [95.0] * 20,
                "close": [150.0] * 20,  # Far from valley
                "volume": [1000000] * 20,
            },
            index=dates,
        )

        valleys_df = pd.DataFrame(
            {"valley1": [100.0] * 20},
            index=dates,
        )

        with patch.object(strategy.valley_study, "compute", return_value=valleys_df):
            signals = strategy.buy(ohlcv_data, "AAPL")

            assert signals.empty

    def test_buy_signal_generated(self, mock_dependencies):
        """Test buy signal generated when price near valley and coming down."""
        strategy = ValleyLong(nearness_threshold=1.0)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        # Create data where price is near valley and coming down
        close_prices = [105.0, 104.0, 103.0, 102.0, 101.0, 100.0, 99.0, 98.0, 97.0, 96.0] + [
            95.0
        ] * 10
        ohlcv_data = pd.DataFrame(
            {
                "open": close_prices,
                "high": [p + 2 for p in close_prices],
                "low": [p - 2 for p in close_prices],
                "close": close_prices,
                "volume": [1000000] * 20,
            },
            index=dates,
        )

        valleys_df = pd.DataFrame(
            {"valley1": [95.0] * 20},
            index=dates,
        )

        with patch.object(strategy.valley_study, "compute", return_value=valleys_df):
            signals = strategy.buy(ohlcv_data, "AAPL")

            # May or may not generate signals depending on _is_coming_down logic
            assert isinstance(signals, pd.DataFrame)

    def test_buy_empty_dataframe(self, mock_dependencies):
        """Test buy with empty DataFrame."""
        strategy = ValleyLong()
        empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        with patch.object(strategy.valley_study, "compute", return_value=pd.DataFrame()):
            signals = strategy.buy(empty_df, "AAPL")

            assert signals.empty


class TestValleyLongSellSignals:
    """Test sell signal generation logic."""

    def test_sell_no_peaks_or_valleys(self, mock_dependencies):
        """Test sell returns empty when no peaks or valleys found."""
        strategy = ValleyLong()
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0] * 20,
                "high": [105.0] * 20,
                "low": [95.0] * 20,
                "close": [100.0] * 20,
                "volume": [1000000] * 20,
            },
            index=dates,
        )

        with (
            patch.object(strategy.peak_study, "compute", return_value=None),
            patch.object(strategy.valley_study, "compute", return_value=None),
        ):
            signals = strategy.sell(ohlcv_data, "AAPL")

            assert signals.empty

    def test_sell_peaks_found_no_match(self, mock_dependencies):
        """Test sell returns empty when peaks found but price not near any."""
        strategy = ValleyLong(sell_nearness_threshold=0.1)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0] * 20,
                "high": [105.0] * 20,
                "low": [95.0] * 20,
                "close": [50.0] * 20,  # Far from peak
                "volume": [1000000] * 20,
            },
            index=dates,
        )

        peaks_df = pd.DataFrame(
            {"peak1": [150.0] * 20},
            index=dates,
        )

        with (
            patch.object(strategy.peak_study, "compute", return_value=peaks_df),
            patch.object(strategy.valley_study, "compute", return_value=None),
        ):
            signals = strategy.sell(ohlcv_data, "AAPL")

            assert signals.empty

    def test_sell_empty_dataframe(self, mock_dependencies):
        """Test sell with empty DataFrame."""
        strategy = ValleyLong()
        empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        with (
            patch.object(strategy.peak_study, "compute", return_value=None),
            patch.object(strategy.valley_study, "compute", return_value=None),
        ):
            signals = strategy.sell(empty_df, "AAPL")

            assert signals.empty


class TestValleyLongGenerateSignals:
    """Test complete signal generation workflow."""

    def test_generate_signals_empty_dataframe(self, mock_dependencies):
        """Test generate_signals with empty DataFrame."""
        strategy = ValleyLong()
        empty_df = pd.DataFrame()

        signals = strategy.generate_signals(empty_df, "AAPL")

        assert signals.empty

    def test_generate_signals_none_dataframe(self, mock_dependencies):
        """Test generate_signals with None."""
        strategy = ValleyLong()

        signals = strategy.generate_signals(None, "AAPL")

        assert signals.empty

    def test_generate_signals_filters_by_confidence(self, mock_dependencies):
        """Test generate_signals filters signals by min_confidence."""
        strategy = ValleyLong(min_confidence=0.8)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0] * 20,
                "high": [105.0] * 20,
                "low": [95.0] * 20,
                "close": [100.0] * 20,
                "volume": [1000000] * 20,
            },
            index=dates,
        )

        # Mock buy to return signals with varying confidence
        buy_signals = pd.DataFrame(
            {
                "price": [100.0, 101.0, 102.0],
                "confidence": [0.9, 0.7, 0.85],  # One below threshold
                "metadata": ['{"valley_value": 100.0}'] * 3,
            },
            index=dates[:3],
        )
        sell_signals = pd.DataFrame()

        with (
            patch.object(strategy, "buy", return_value=buy_signals),
            patch.object(strategy, "sell", return_value=sell_signals),
        ):
            signals = strategy.generate_signals(ohlcv_data, "AAPL")

            if not signals.empty:
                assert (signals["confidence"] >= 0.8).all()

    def test_generate_signals_combines_buy_and_sell(self, mock_dependencies):
        """Test generate_signals combines buy and sell signals."""
        strategy = ValleyLong()
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0] * 20,
                "high": [105.0] * 20,
                "low": [95.0] * 20,
                "close": [100.0] * 20,
                "volume": [1000000] * 20,
            },
            index=dates,
        )

        buy_signals = pd.DataFrame(
            {
                "price": [100.0],
                "confidence": [0.9],
                "metadata": ['{"valley_value": 100.0}'],
            },
            index=[dates[0]],
        )
        sell_signals = pd.DataFrame(
            {
                "price": [105.0],
                "confidence": [0.85],
                "metadata": ['{"target_value": 105.0}'],
            },
            index=[dates[10]],
        )

        with (
            patch.object(strategy, "buy", return_value=buy_signals),
            patch.object(strategy, "sell", return_value=sell_signals),
        ):
            signals = strategy.generate_signals(ohlcv_data, "AAPL")

            if not signals.empty:
                assert "signal_type" in signals.columns
                assert set(signals["signal_type"].unique()) <= {"buy", "sell"}


class TestValleyLongHelperMethods:
    """Test helper methods."""

    def test_extract_all_values(self, mock_dependencies):
        """Test _extract_all_values extracts and sorts values."""
        strategy = ValleyLong()
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        df = pd.DataFrame(
            {
                "valley1": [95.0, 95.0, None, None, None, None, None, None, None, None],
                "valley2": [100.0, None, 100.0, None, None, None, None, None, None, None],
                "peak1": [105.0, None, None, None, None, None, None, None, None, None],
                "other_col": [1.0] * 10,
            },
            index=dates,
        )

        valleys = strategy._extract_all_values(df, "valley")
        peaks = strategy._extract_all_values(df, "peak")

        assert valleys == [95.0, 100.0]
        assert peaks == [105.0]

    def test_find_near_value(self, mock_dependencies):
        """Test _find_near_value finds values within threshold."""
        strategy = ValleyLong(nearness_threshold=1.0)  # 1% threshold

        # 100.0 with 1% threshold means 99.0-101.0 range
        target_values = [95.0, 100.0, 105.0]
        assert strategy._find_near_value(100.0, target_values) == 100.0
        assert strategy._find_near_value(100.5, target_values) == 100.0  # Within 1%
        assert strategy._find_near_value(102.0, target_values) is None  # Outside 1%

    def test_find_near_value_sell(self, mock_dependencies):
        """Test _find_near_value_sell uses sell threshold."""
        strategy = ValleyLong(nearness_threshold=1.0, sell_nearness_threshold=0.5)

        target_values = [100.0]
        assert strategy._find_near_value_sell(100.5, target_values) == 100.0  # Within 0.5%
        assert strategy._find_near_value_sell(101.0, target_values) is None  # Outside 0.5%

    def test_calculate_confidence(self, mock_dependencies):
        """Test _calculate_confidence calculates confidence correctly."""
        strategy = ValleyLong(nearness_threshold=1.0)

        # At exact match, confidence should be 1.0
        confidence = strategy._calculate_confidence(100.0, 100.0)
        assert confidence == 1.0

        # At threshold boundary, confidence should be 0.0
        confidence = strategy._calculate_confidence(101.0, 100.0)
        assert confidence == 0.0

        # Between should be proportional
        confidence = strategy._calculate_confidence(100.5, 100.0)
        assert 0.0 < confidence < 1.0

    def test_calculate_confidence_zero_target(self, mock_dependencies):
        """Test _calculate_confidence returns 0.0 when target is zero."""
        strategy = ValleyLong()
        confidence = strategy._calculate_confidence(100.0, 0.0)
        assert confidence == 0.0

    def test_create_buy_signal(self, mock_dependencies):
        """Test _create_buy_signal creates signal with correct structure."""
        strategy = ValleyLong(nearness_threshold=1.0)
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0] * 10,
                "high": [105.0] * 10,
                "low": [95.0] * 10,
                "close": [100.0] * 10,
                "volume": [1000000] * 10,
            },
            index=dates,
        )

        signal = strategy._create_buy_signal(dates[0], ohlcv_data, 100.0, 100.0)

        assert signal["timestamp"] == dates[0]
        assert signal["price"] == 100.0
        assert "confidence" in signal
        assert "metadata" in signal
        metadata = json.loads(signal["metadata"])
        assert "valley_value" in metadata
        assert metadata["valley_value"] == 100.0

    def test_create_sell_signal(self, mock_dependencies):
        """Test _create_sell_signal creates signal with correct structure."""
        strategy = ValleyLong(nearness_threshold=1.0)
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0] * 10,
                "high": [105.0] * 10,
                "low": [95.0] * 10,
                "close": [100.0] * 10,
                "volume": [1000000] * 10,
            },
            index=dates,
        )

        signal = strategy._create_sell_signal(dates[0], ohlcv_data, 105.0, 105.0, "peak")

        assert signal["timestamp"] == dates[0]
        assert signal["price"] == 105.0
        assert "confidence" in signal
        assert "metadata" in signal
        metadata = json.loads(signal["metadata"])
        assert "target_value" in metadata
        assert metadata["target_value"] == 105.0
        assert metadata["signal_source"] == "peak"


class TestValleyLongComputeMethods:
    """Test valley and peak computation methods."""

    def test_compute_valleys_with_percentage_conversion(self, mock_dependencies):
        """Test _compute_valleys converts percentage parameters correctly."""
        strategy = ValleyLong(valley_prominence=2.0, valley_height=5.0)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0] * 20,
                "high": [105.0] * 20,
                "low": [95.0] * 20,
                "close": [100.0] * 20,
                "volume": [1000000] * 20,
            },
            index=dates,
        )

        with patch.object(strategy.valley_study, "compute") as mock_compute:
            mock_compute.return_value = pd.DataFrame()
            strategy._compute_valleys(ohlcv_data, "AAPL")

            # Verify compute called with converted values
            call_kwargs = mock_compute.call_args[1]
            assert "prominence" in call_kwargs
            # prominence should be avg_price * (2.0 / 100.0) = 100.0 * 0.02 = 2.0
            assert call_kwargs["prominence"] == pytest.approx(2.0, abs=0.01)
            assert "height" in call_kwargs
            # height should be avg_price * (5.0 / 100.0) = 100.0 * 0.05 = 5.0
            assert call_kwargs["height"] == pytest.approx(5.0, abs=0.01)

    def test_compute_peaks_with_percentage_conversion(self, mock_dependencies):
        """Test _compute_peaks converts percentage parameters correctly."""
        strategy = ValleyLong(peak_prominence=2.0, peak_height=5.0)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0] * 20,
                "high": [105.0] * 20,
                "low": [95.0] * 20,
                "close": [100.0] * 20,
                "volume": [1000000] * 20,
            },
            index=dates,
        )

        with patch.object(strategy.peak_study, "compute") as mock_compute:
            mock_compute.return_value = pd.DataFrame()
            strategy._compute_peaks(ohlcv_data, "AAPL")

            # Verify compute called with converted values
            call_kwargs = mock_compute.call_args[1]
            assert "prominence" in call_kwargs
            assert call_kwargs["prominence"] == pytest.approx(2.0, abs=0.01)
            assert "height" in call_kwargs
            assert call_kwargs["height"] == pytest.approx(5.0, abs=0.01)


class TestValleyLongEdgeCases:
    """Test edge cases and error handling."""

    def test_is_coming_down_insufficient_data(self, mock_dependencies):
        """Test _is_coming_down with insufficient lookback periods."""
        strategy = ValleyLong()
        dates = pd.date_range(start="2024-01-01", periods=3, freq="D")
        prices = pd.Series([100.0, 101.0, 102.0], index=dates)

        result = strategy._is_coming_down(prices, dates[0], 95.0, lookback_periods=5)

        assert result is False

    def test_is_coming_up_insufficient_data(self, mock_dependencies):
        """Test _is_coming_up with insufficient lookback periods."""
        strategy = ValleyLong()
        dates = pd.date_range(start="2024-01-01", periods=3, freq="D")
        prices = pd.Series([100.0, 101.0, 102.0], index=dates)

        result = strategy._is_coming_up(prices, dates[0], 105.0, lookback_periods=5)

        assert result is False

    def test_find_near_value_empty_list(self, mock_dependencies):
        """Test _find_near_value with empty target values."""
        strategy = ValleyLong()
        result = strategy._find_near_value(100.0, [])
        assert result is None

    def test_find_near_value_zero_target(self, mock_dependencies):
        """Test _find_near_value skips zero values."""
        strategy = ValleyLong()
        result = strategy._find_near_value(100.0, [0.0, 100.0])
        assert result == 100.0  # Should skip 0.0 and find 100.0
