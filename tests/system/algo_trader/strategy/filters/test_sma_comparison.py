"""Unit tests for SmaComparisonFilter - SMA Comparison Filter.

Tests cover initialization, evaluation, SMA computation, and error handling.
All external dependencies are mocked via conftest.py.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.strategy.filters.base import BaseComparisonFilter
from system.algo_trader.strategy.filters.core import FilterContext
from system.algo_trader.strategy.filters.sma_comparison import SmaComparisonFilter


class TestSmaComparisonFilterInitialization:
    """Test SmaComparisonFilter initialization."""

    def test_initialization_with_signal_fields(self, mock_logger):
        """Test initialization with signal field names only."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast", field_slow="sma_slow", operator=">", logger=mock_logger
        )

        assert filter_instance.field_fast == "sma_fast"
        assert filter_instance.field_slow == "sma_slow"
        assert filter_instance.operator == ">"
        assert filter_instance.fast_window is None
        assert filter_instance.slow_window is None

    def test_initialization_with_windows(self, mock_logger):
        """Test initialization with SMA windows."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast",
            field_slow="sma_slow",
            operator=">",
            windows=(5, 10),
            logger=mock_logger,
        )

        assert filter_instance.fast_window == 5
        assert filter_instance.slow_window == 10

    def test_initialization_inherits_from_base(self, mock_logger):
        """Test that SmaComparisonFilter inherits from BaseComparisonFilter."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast", field_slow="sma_slow", operator=">", logger=mock_logger
        )

        assert isinstance(filter_instance, BaseComparisonFilter)


class TestSmaComparisonFilterEvaluation:
    """Test SmaComparisonFilter evaluation logic."""

    def test_evaluate_from_signal_fields_success(self, filter_context, mock_logger):
        """Test evaluation using signal field values."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast", field_slow="sma_slow", operator=">", logger=mock_logger
        )
        filter_context.signal["sma_fast"] = 150.0
        filter_context.signal["sma_slow"] = 100.0

        result = filter_instance.evaluate(filter_context)

        assert result is True

    def test_evaluate_from_signal_fields_failure(self, filter_context, mock_logger):
        """Test evaluation fails when fast <= slow."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast", field_slow="sma_slow", operator=">", logger=mock_logger
        )
        filter_context.signal["sma_fast"] = 100.0
        filter_context.signal["sma_slow"] = 150.0

        result = filter_instance.evaluate(filter_context)

        assert result is False

    def test_evaluate_missing_ticker_returns_false(self, filter_context, mock_logger):
        """Test evaluation when ticker is missing returns False."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast", field_slow="sma_slow", operator=">", logger=mock_logger
        )
        del filter_context.signal["ticker"]

        result = filter_instance.evaluate(filter_context)

        assert result is False
        mock_logger.debug.assert_called()

    def test_evaluate_missing_signal_fields_returns_false(self, filter_context, mock_logger):
        """Test evaluation when signal fields are missing returns False."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast", field_slow="sma_slow", operator=">", logger=mock_logger
        )
        # No OHLCV data and no signal fields
        filter_context.ohlcv_by_ticker = {}

        result = filter_instance.evaluate(filter_context)

        assert result is False
        mock_logger.debug.assert_called()

    @patch("system.algo_trader.strategy.filters.sma_comparison.SimpleMovingAverage")
    def test_evaluate_from_ohlcv_success(self, mock_sma_class, filter_context, mock_logger):
        """Test evaluation computing SMA from OHLCV data."""
        # Setup mock SMA study
        mock_sma_instance = MagicMock()
        mock_sma_class.return_value = mock_sma_instance

        # Create SMA result DataFrame
        sma_result = pd.DataFrame({"sma": [150.0, 100.0]}, index=[0, 1])
        mock_sma_instance.compute.return_value = sma_result

        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast",
            field_slow="sma_slow",
            operator=">",
            windows=(5, 10),
            logger=mock_logger,
        )

        # Replace the sma_study with our mock
        filter_instance.sma_study = mock_sma_instance

        # Setup OHLCV data
        ohlcv = pd.DataFrame(
            {
                "open": [100.0] * 15,
                "high": [105.0] * 15,
                "low": [95.0] * 15,
                "close": list(range(100, 115)),
                "volume": [1000000] * 15,
            }
        )
        filter_context.ohlcv_by_ticker["AAPL"] = ohlcv

        # Mock the _get_sma_value method to return expected values
        filter_instance._get_sma_value = MagicMock(side_effect=[150.0, 100.0])

        result = filter_instance.evaluate(filter_context)

        assert result is True

    def test_evaluate_insufficient_ohlcv_data_returns_false(self, filter_context, mock_logger):
        """Test evaluation with insufficient OHLCV data returns False."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast",
            field_slow="sma_slow",
            operator=">",
            windows=(20, 30),
            logger=mock_logger,
        )

        # Create insufficient OHLCV data
        ohlcv = pd.DataFrame(
            {
                "open": [100.0] * 10,
                "high": [105.0] * 10,
                "low": [95.0] * 10,
                "close": [100.0] * 10,
                "volume": [1000000] * 10,
            }
        )
        filter_context.ohlcv_by_ticker["AAPL"] = ohlcv

        # Mock _get_sma_value to return None (insufficient data)
        filter_instance._get_sma_value = MagicMock(return_value=None)

        result = filter_instance.evaluate(filter_context)

        assert result is False
        mock_logger.debug.assert_called()


class TestSmaComparisonFilterFromConfig:
    """Test SmaComparisonFilter.from_config class method."""

    def test_from_config_success_with_fields_only(self, mock_logger):
        """Test creating filter from config with fields only."""
        params = {
            "field_fast": "sma_fast",
            "field_slow": "sma_slow",
            "operator": ">",
        }
        result = SmaComparisonFilter.from_config(params, mock_logger)

        assert result is not None
        assert isinstance(result, SmaComparisonFilter)
        assert result.field_fast == "sma_fast"
        assert result.field_slow == "sma_slow"
        assert result.fast_window is None
        assert result.slow_window is None

    def test_from_config_success_with_windows(self, mock_logger):
        """Test creating filter from config with windows."""
        params = {
            "field_fast": "sma_fast",
            "field_slow": "sma_slow",
            "operator": ">",
            "fast_window": 5,
            "slow_window": 10,
        }
        result = SmaComparisonFilter.from_config(params, mock_logger)

        assert result is not None
        assert result.fast_window == 5
        assert result.slow_window == 10

    def test_from_config_missing_field_fast(self, mock_logger):
        """Test from_config with missing field_fast parameter."""
        params = {"field_slow": "sma_slow", "operator": ">"}
        result = SmaComparisonFilter.from_config(params, mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    def test_from_config_missing_field_slow(self, mock_logger):
        """Test from_config with missing field_slow parameter."""
        params = {"field_fast": "sma_fast", "operator": ">"}
        result = SmaComparisonFilter.from_config(params, mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    def test_from_config_missing_operator(self, mock_logger):
        """Test from_config with missing operator parameter."""
        params = {"field_fast": "sma_fast", "field_slow": "sma_slow"}
        result = SmaComparisonFilter.from_config(params, mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    def test_from_config_partial_windows(self, mock_logger):
        """Test from_config with only one window specified."""
        params = {
            "field_fast": "sma_fast",
            "field_slow": "sma_slow",
            "operator": ">",
            "fast_window": 5,
        }
        result = SmaComparisonFilter.from_config(params, mock_logger)

        assert result is not None
        assert result.fast_window == 5
        assert result.slow_window is None


class TestSmaComparisonFilterHelperMethods:
    """Test SmaComparisonFilter helper methods."""

    def test_get_sma_value_success(self, mock_logger):
        """Test _get_sma_value computes SMA correctly."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast", field_slow="sma_slow", operator=">", logger=mock_logger
        )

        ohlcv = pd.DataFrame(
            {
                "open": [100.0] * 15,
                "high": [105.0] * 15,
                "low": [95.0] * 15,
                "close": list(range(100, 115)),
                "volume": [1000000] * 15,
            }
        )

        # Mock the SMA study compute method
        with patch.object(
            filter_instance.sma_study, "compute", return_value=pd.DataFrame({"sma": [107.0]})
        ):
            result = filter_instance._get_sma_value(ohlcv, 10, "AAPL")

            assert result == 107.0

    def test_get_sma_value_empty_ohlcv_returns_none(self, mock_logger):
        """Test _get_sma_value with empty OHLCV returns None."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast", field_slow="sma_slow", operator=">", logger=mock_logger
        )

        result = filter_instance._get_sma_value(pd.DataFrame(), 10, "AAPL")

        assert result is None

    def test_get_sma_value_insufficient_data_returns_none(self, mock_logger):
        """Test _get_sma_value with insufficient data returns None."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast", field_slow="sma_slow", operator=">", logger=mock_logger
        )

        ohlcv = pd.DataFrame(
            {
                "open": [100.0] * 5,
                "high": [105.0] * 5,
                "low": [95.0] * 5,
                "close": [100.0] * 5,
                "volume": [1000000] * 5,
            }
        )

        result = filter_instance._get_sma_value(ohlcv, 10, "AAPL")

        assert result is None

    def test_get_value_from_signal_success(self, mock_logger):
        """Test _get_value_from_signal extracts numeric value."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast", field_slow="sma_slow", operator=">", logger=mock_logger
        )

        signal = {"sma_fast": 150.0}
        result = filter_instance._get_value_from_signal(signal, "sma_fast")

        assert result == 150.0

    def test_get_value_from_signal_missing_field_returns_none(self, mock_logger):
        """Test _get_value_from_signal with missing field returns None."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast", field_slow="sma_slow", operator=">", logger=mock_logger
        )

        signal = {}
        result = filter_instance._get_value_from_signal(signal, "sma_fast")

        assert result is None

    def test_get_value_from_signal_non_numeric_returns_none(self, mock_logger):
        """Test _get_value_from_signal with non-numeric value returns None."""
        filter_instance = SmaComparisonFilter(
            field_fast="sma_fast", field_slow="sma_slow", operator=">", logger=mock_logger
        )

        signal = {"sma_fast": "not_a_number"}
        result = filter_instance._get_value_from_signal(signal, "sma_fast")

        assert result is None

