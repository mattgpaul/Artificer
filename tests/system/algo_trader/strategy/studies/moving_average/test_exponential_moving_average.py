"""Unit tests for ExponentialMovingAverage - EMA Study.

Tests cover initialization, field name generation, validation, calculation,
and error handling. All external dependencies are mocked via conftest.py.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.strategy.studies.moving_average.exponential_moving_average import (
    ExponentialMovingAverage,
)


class TestExponentialMovingAverageInitialization:
    """Test ExponentialMovingAverage initialization."""

    def test_initialization(self, mock_logger):
        """Test ExponentialMovingAverage initialization."""
        study = ExponentialMovingAverage(logger=mock_logger)

        assert study.logger == mock_logger

    def test_initialization_creates_logger(self):
        """Test initialization creates logger if not provided."""
        with patch("system.algo_trader.strategy.studies.base_study.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            study = ExponentialMovingAverage()

            assert study.logger == mock_logger


class TestExponentialMovingAverageFieldName:
    """Test ExponentialMovingAverage field name generation."""

    def test_get_field_name(self, mock_logger):
        """Test get_field_name returns correct field name."""
        study = ExponentialMovingAverage(logger=mock_logger)

        field_name = study.get_field_name(window=10)

        assert field_name == "ema_10"

    def test_get_field_name_missing_window_raises(self, mock_logger):
        """Test get_field_name raises ValueError when window is missing."""
        study = ExponentialMovingAverage(logger=mock_logger)

        with pytest.raises(ValueError, match="window parameter is required"):
            study.get_field_name()


class TestExponentialMovingAverageValidation:
    """Test ExponentialMovingAverage validation."""

    def test_validate_study_specific_success(self, mock_logger):
        """Test _validate_study_specific with valid data."""
        study = ExponentialMovingAverage(logger=mock_logger)

        ohlcv_data = pd.DataFrame(
            {"close": [100.0] * 20},
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=20, freq="1D", tz="UTC")),
        )

        result = study._validate_study_specific(ohlcv_data, "AAPL", window=10)

        assert result is True

    def test_validate_study_specific_missing_window(self, mock_logger):
        """Test _validate_study_specific with missing window."""
        study = ExponentialMovingAverage(logger=mock_logger)

        ohlcv_data = pd.DataFrame({"close": [100.0] * 20})

        result = study._validate_study_specific(ohlcv_data, "AAPL")

        assert result is False
        mock_logger.debug.assert_called()

    def test_validate_study_specific_insufficient_data(self, mock_logger):
        """Test _validate_study_specific with insufficient data."""
        study = ExponentialMovingAverage(logger=mock_logger)

        ohlcv_data = pd.DataFrame(
            {"close": [100.0] * 5},  # Only 5 bars, need 10
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")),
        )

        result = study._validate_study_specific(ohlcv_data, "AAPL", window=10)

        assert result is False
        mock_logger.debug.assert_called()


class TestExponentialMovingAverageCalculation:
    """Test ExponentialMovingAverage calculation."""

    def test_calculate_success(self, mock_logger):
        """Test calculate with valid data."""
        study = ExponentialMovingAverage(logger=mock_logger)

        ohlcv_data = pd.DataFrame(
            {"close": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0]},
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1D", tz="UTC")),
        )

        result = study.calculate(ohlcv_data, "AAPL", window=5, column="close")

        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(ohlcv_data)

    def test_calculate_missing_window(self, mock_logger):
        """Test calculate with missing window."""
        study = ExponentialMovingAverage(logger=mock_logger)

        ohlcv_data = pd.DataFrame({"close": [100.0] * 10})

        result = study.calculate(ohlcv_data, "AAPL", column="close")

        assert result is None
        mock_logger.debug.assert_called()

    def test_calculate_missing_column(self, mock_logger):
        """Test calculate with missing column."""
        study = ExponentialMovingAverage(logger=mock_logger)

        ohlcv_data = pd.DataFrame({"open": [100.0] * 10})

        result = study.calculate(ohlcv_data, "AAPL", window=5, column="close")

        assert result is None
        mock_logger.debug.assert_called()

    def test_calculate_default_column(self, mock_logger):
        """Test calculate uses 'close' as default column."""
        study = ExponentialMovingAverage(logger=mock_logger)

        ohlcv_data = pd.DataFrame(
            {"close": [100.0] * 10},
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1D", tz="UTC")),
        )

        result = study.calculate(ohlcv_data, "AAPL", window=5)

        assert result is not None

    def test_compute_success(self, mock_logger):
        """Test compute method with valid data."""
        study = ExponentialMovingAverage(logger=mock_logger)

        ohlcv_data = pd.DataFrame(
            {"close": [100.0] * 10},
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=10, freq="1D", tz="UTC")),
        )

        result = study.compute(ohlcv_data, window=5, ticker="AAPL", column="close")

        assert result is not None
        assert isinstance(result, pd.Series)
