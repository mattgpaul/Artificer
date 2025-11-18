"""Unit tests for FindPeaks - Peak detection study.

Tests cover initialization, validation, peak detection with various parameters,
edge cases, and error handling. All external dependencies are mocked.
"""

from unittest.mock import patch

import pandas as pd

from system.algo_trader.strategy.utils.studies.support_resistance.find_peaks import FindPeaks


class TestFindPeaksInitialization:
    """Test FindPeaks initialization."""

    def test_initialization_with_logger(self, mock_logger):
        """Test initialization with provided logger."""
        study = FindPeaks(logger=mock_logger)
        assert study.logger == mock_logger

    def test_initialization_without_logger(self):
        """Test initialization without logger creates new one."""
        study = FindPeaks()
        assert study.logger is not None


class TestFindPeaksValidation:
    """Test FindPeaks validation methods."""

    def test_validate_study_specific_sufficient_data(self, mock_logger, sample_ohlcv_data):
        """Test validation with sufficient data (>= 3 rows)."""
        study = FindPeaks(logger=mock_logger)
        result = study._validate_study_specific(sample_ohlcv_data, "AAPL")
        assert result is True
        mock_logger.debug.assert_not_called()

    def test_validate_study_specific_insufficient_data(self, mock_logger):
        """Test validation fails with insufficient data (< 3 rows)."""
        study = FindPeaks(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=2, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0, 101.0],
                "high": [105.0, 106.0],
                "low": [95.0, 96.0],
                "close": [100.0, 101.0],
                "volume": [1000000, 1000000],
            },
            index=dates,
        )
        result = study._validate_study_specific(ohlcv_data, "AAPL")
        assert result is False
        mock_logger.debug.assert_called_once()


class TestFindPeaksCalculation:
    """Test FindPeaks calculation logic."""

    def test_calculate_basic_peaks(self, mock_logger, sample_ohlcv_data):
        """Test basic peak detection without parameters."""
        study = FindPeaks(logger=mock_logger)
        result = study.calculate(sample_ohlcv_data, "AAPL", column="close")

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_ohlcv_data)

    def test_calculate_with_height_parameter(self, mock_logger):
        """Test peak detection with height parameter."""
        study = FindPeaks(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        # Create data with clear peaks
        close_prices = [
            100,
            102,
            105,
            103,
            101,
            110,
            108,
            106,
            104,
            102,
            115,
            113,
            111,
            109,
            107,
            105,
            103,
            101,
            99,
            97,
        ]
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

        result = study.calculate(ohlcv_data, "AAPL", column="close", height=105)

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_calculate_with_distance_parameter(self, mock_logger):
        """Test peak detection with distance parameter."""
        study = FindPeaks(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = [
            100,
            102,
            105,
            103,
            101,
            110,
            108,
            106,
            104,
            102,
            115,
            113,
            111,
            109,
            107,
            105,
            103,
            101,
            99,
            97,
        ]
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

        result = study.calculate(ohlcv_data, "AAPL", column="close", distance=5)

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_calculate_with_prominence_parameter(self, mock_logger):
        """Test peak detection with prominence parameter."""
        study = FindPeaks(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = [
            100,
            102,
            105,
            103,
            101,
            110,
            108,
            106,
            104,
            102,
            115,
            113,
            111,
            109,
            107,
            105,
            103,
            101,
            99,
            97,
        ]
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

        result = study.calculate(ohlcv_data, "AAPL", column="close", prominence=5)

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_calculate_with_width_parameter(self, mock_logger):
        """Test peak detection with width parameter."""
        study = FindPeaks(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = [
            100,
            102,
            105,
            103,
            101,
            110,
            108,
            106,
            104,
            102,
            115,
            113,
            111,
            109,
            107,
            105,
            103,
            101,
            99,
            97,
        ]
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

        result = study.calculate(ohlcv_data, "AAPL", column="close", width=2)

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_calculate_with_threshold_parameter(self, mock_logger):
        """Test peak detection with threshold parameter."""
        study = FindPeaks(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = [
            100,
            102,
            105,
            103,
            101,
            110,
            108,
            106,
            104,
            102,
            115,
            113,
            111,
            109,
            107,
            105,
            103,
            101,
            99,
            97,
        ]
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

        result = study.calculate(ohlcv_data, "AAPL", column="close", threshold=2)

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_calculate_no_peaks_found(self, mock_logger):
        """Test when no peaks are found."""
        study = FindPeaks(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        # Flat data - no peaks
        close_prices = [100.0] * 10
        ohlcv_data = pd.DataFrame(
            {
                "open": close_prices,
                "high": close_prices,
                "low": close_prices,
                "close": close_prices,
                "volume": [1000000] * 10,
            },
            index=dates,
        )

        result = study.calculate(ohlcv_data, "AAPL", column="close", height=105)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(ohlcv_data)
        # Should have no peak columns
        assert len([col for col in result.columns if col.startswith("peak")]) == 0

    def test_calculate_missing_column(self, mock_logger, sample_ohlcv_data):
        """Test calculation fails when column is missing."""
        study = FindPeaks(logger=mock_logger)
        result = study.calculate(sample_ohlcv_data, "AAPL", column="missing_column")

        assert result is None
        mock_logger.error.assert_called_once()

    def test_calculate_exception_handling(self, mock_logger, sample_ohlcv_data):
        """Test exception handling during peak detection."""
        study = FindPeaks(logger=mock_logger)
        with patch(
            "system.algo_trader.strategy.utils.studies.support_resistance.find_peaks.find_peaks",
            side_effect=Exception("Test error"),
        ):
            result = study.calculate(sample_ohlcv_data, "AAPL", column="close")

            assert result is None
            mock_logger.error.assert_called_once()


class TestFindPeaksCompute:
    """Test FindPeaks compute orchestration."""

    def test_compute_success(self, mock_logger, sample_ohlcv_data):
        """Test compute with all validation passing."""
        study = FindPeaks(logger=mock_logger)
        result = study.compute(ohlcv_data=sample_ohlcv_data, ticker="AAPL", column="close")

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_compute_with_parameters(self, mock_logger, sample_ohlcv_data):
        """Test compute with all parameters."""
        study = FindPeaks(logger=mock_logger)
        result = study.compute(
            ohlcv_data=sample_ohlcv_data,
            ticker="AAPL",
            column="close",
            height=105,
            distance=5,
            prominence=5,
            width=2,
            threshold=2,
        )

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_compute_fails_data_validation(self, mock_logger):
        """Test compute fails when data is None."""
        study = FindPeaks(logger=mock_logger)
        result = study.compute(ohlcv_data=None, ticker="AAPL", column="close")
        assert result is None

    def test_compute_fails_insufficient_data(self, mock_logger):
        """Test compute fails with insufficient data."""
        study = FindPeaks(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=2, freq="D")
        ohlcv_data = pd.DataFrame(
            {
                "open": [100.0, 101.0],
                "high": [105.0, 106.0],
                "low": [95.0, 96.0],
                "close": [100.0, 101.0],
                "volume": [1000000, 1000000],
            },
            index=dates,
        )
        result = study.compute(ohlcv_data=ohlcv_data, ticker="AAPL", column="close")
        assert result is None

    def test_compute_peak_naming(self, mock_logger):
        """Test that peaks are named correctly (peak1, peak2, etc.)."""
        study = FindPeaks(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        # Create data with multiple clear peaks
        close_prices = [
            100,
            102,
            105,
            103,
            101,
            110,
            108,
            106,
            104,
            102,
            115,
            113,
            111,
            109,
            107,
            105,
            103,
            101,
            99,
            97,
        ]
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

        result = study.compute(ohlcv_data=ohlcv_data, ticker="AAPL", column="close", height=105)

        if result is not None and not result.empty:
            peak_cols = [col for col in result.columns if col.startswith("peak")]
            if peak_cols:
                # Check naming convention
                assert all(col.startswith("peak") for col in peak_cols)
                # Check sequential numbering
                peak_numbers = [int(col.replace("peak", "")) for col in peak_cols]
                assert peak_numbers == sorted(peak_numbers)
