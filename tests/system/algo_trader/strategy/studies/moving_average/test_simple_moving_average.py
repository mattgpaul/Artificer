"""Unit tests for SimpleMovingAverage - SMA Technical Indicator Study.

Tests cover initialization, validation, calculation, and error handling.
All external dependencies are mocked to avoid logging calls.
"""

import numpy as np
import pandas as pd
import pytest

from system.algo_trader.strategy.studies.moving_average.simple_moving_average import (
    SimpleMovingAverage,
)


class TestSimpleMovingAverageInitialization:
    """Test SimpleMovingAverage initialization."""

    def test_initialization_with_logger(self, mock_logger):
        """Test initialization with provided logger."""
        study = SimpleMovingAverage(logger=mock_logger)
        assert study.logger == mock_logger

    def test_initialization_without_logger(self):
        """Test initialization without logger creates new one."""
        study = SimpleMovingAverage()
        assert study.logger is not None


class TestSimpleMovingAverageValidation:
    """Test SimpleMovingAverage validation methods."""

    def test_validate_study_specific_sufficient_data(self, mock_logger, sample_ohlcv_data):
        """Test study-specific validation with sufficient data."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study._validate_study_specific(sample_ohlcv_data, "AAPL", window=10)
        assert result is True

    def test_validate_study_specific_insufficient_data(self, mock_logger, sample_ohlcv_data):
        """Test study-specific validation with insufficient data."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study._validate_study_specific(sample_ohlcv_data, "AAPL", window=50)
        assert result is False
        mock_logger.debug.assert_called()

    def test_validate_study_specific_missing_window(self, mock_logger, sample_ohlcv_data):
        """Test study-specific validation fails when window is missing."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study._validate_study_specific(sample_ohlcv_data, "AAPL")
        assert result is False
        mock_logger.debug.assert_called()

    def test_validate_study_specific_exact_window_size(self, mock_logger, sample_ohlcv_data):
        """Test study-specific validation with exact window size."""
        study = SimpleMovingAverage(logger=mock_logger)
        # Create data with exactly 10 rows
        exact_data = sample_ohlcv_data.head(10)
        result = study._validate_study_specific(exact_data, "AAPL", window=10)
        assert result is True


class TestSimpleMovingAverageCalculation:
    """Test SimpleMovingAverage calculation methods."""

    def test_calculate_success(self, mock_logger, sample_ohlcv_data):
        """Test calculate returns correct SMA values."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study.calculate(sample_ohlcv_data, "AAPL", window=5, column="close")
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv_data)
        # First 4 values should be NaN (insufficient data for window=5)
        assert pd.isna(result.iloc[:4]).all()
        # 5th value should be the mean of first 5 values
        assert result.iloc[4] == sample_ohlcv_data["close"].iloc[:5].mean()

    def test_calculate_missing_window(self, mock_logger, sample_ohlcv_data):
        """Test calculate fails when window is missing."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study.calculate(sample_ohlcv_data, "AAPL", column="close")
        assert result is None
        mock_logger.error.assert_called()

    def test_calculate_missing_column(self, mock_logger, sample_ohlcv_data):
        """Test calculate fails when column is missing."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study.calculate(sample_ohlcv_data, "AAPL", window=5, column="missing_col")
        assert result is None
        mock_logger.error.assert_called()

    def test_calculate_different_column(self, mock_logger, sample_ohlcv_data):
        """Test calculate works with different column."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study.calculate(sample_ohlcv_data, "AAPL", window=5, column="open")
        assert result is not None
        assert isinstance(result, pd.Series)
        assert result.iloc[4] == sample_ohlcv_data["open"].iloc[:5].mean()

    def test_calculate_with_nan_values(self, mock_logger, sample_ohlcv_data):
        """Test calculate handles NaN values in data."""
        study = SimpleMovingAverage(logger=mock_logger)
        # Insert NaN values
        sample_ohlcv_data.loc[sample_ohlcv_data.index[5], "close"] = np.nan
        result = study.calculate(sample_ohlcv_data, "AAPL", window=5, column="close")
        assert result is not None
        # Rolling mean handles NaN appropriately
        assert isinstance(result, pd.Series)


class TestSimpleMovingAverageCompute:
    """Test SimpleMovingAverage compute method."""

    def test_compute_success(self, mock_logger, sample_ohlcv_data):
        """Test compute with all validation passing."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study.compute(
            ohlcv_data=sample_ohlcv_data, window=10, ticker="AAPL", column="close"
        )
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv_data)

    def test_compute_fails_data_validation(self, mock_logger):
        """Test compute fails when data is None."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study.compute(ohlcv_data=None, window=10, ticker="AAPL")
        assert result is None

    def test_compute_fails_column_validation(self, mock_logger, ohlcv_data_missing_close):
        """Test compute fails when required column is missing."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study.compute(
            ohlcv_data=ohlcv_data_missing_close, window=10, ticker="AAPL", column="close"
        )
        assert result is None

    def test_compute_fails_insufficient_data(self, mock_logger, sample_ohlcv_data):
        """Test compute fails when data is insufficient."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study.compute(ohlcv_data=sample_ohlcv_data, window=50, ticker="AAPL")
        assert result is None

    @pytest.mark.parametrize("window,expected_nan_count", [(5, 4), (10, 9), (20, 19)])
    def test_compute_different_windows(
        self, mock_logger, sample_ohlcv_data, window, expected_nan_count
    ):
        """Test compute with different window sizes."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study.compute(
            ohlcv_data=sample_ohlcv_data, window=window, ticker="AAPL", column="close"
        )
        assert result is not None
        # Count NaN values (should be window - 1)
        nan_count = result.isna().sum()
        assert nan_count == expected_nan_count

    def test_compute_default_column(self, mock_logger, sample_ohlcv_data):
        """Test compute uses 'close' column by default."""
        study = SimpleMovingAverage(logger=mock_logger)
        result = study.compute(ohlcv_data=sample_ohlcv_data, window=10, ticker="AAPL")
        assert result is not None
        # Verify it calculated using 'close' column
        assert result.iloc[9] == sample_ohlcv_data["close"].iloc[:10].mean()
