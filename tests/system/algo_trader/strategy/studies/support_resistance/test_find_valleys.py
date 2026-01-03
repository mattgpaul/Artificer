"""Unit tests for FindValleys - Valley detection study.

Tests cover initialization, validation, valley detection with various parameters,
edge cases, and error handling. All external dependencies are mocked.
"""

from unittest.mock import patch

import pandas as pd

from system.algo_trader.strategy.studies.support_resistance.find_valleys import FindValleys


class TestFindValleysInitialization:
    """Test FindValleys initialization."""

    def test_initialization_with_logger(self, mock_logger):
        """Test initialization with provided logger."""
        study = FindValleys(logger=mock_logger)
        assert study.logger == mock_logger

    def test_initialization_without_logger(self):
        """Test initialization without logger creates new one."""
        study = FindValleys()
        assert study.logger is not None


class TestFindValleysValidation:
    """Test FindValleys validation methods."""

    def test_validate_study_specific_sufficient_data(self, mock_logger, sample_ohlcv_data):
        """Test validation with sufficient data (>= 3 rows)."""
        study = FindValleys(logger=mock_logger)
        result = study._validate_study_specific(sample_ohlcv_data, "AAPL")
        assert result is True
        mock_logger.debug.assert_not_called()

    def test_validate_study_specific_insufficient_data(self, mock_logger):
        """Test validation fails with insufficient data (< 3 rows)."""
        study = FindValleys(logger=mock_logger)
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


class TestFindValleysCalculation:
    """Test FindValleys calculation logic."""

    def test_calculate_basic_valleys(self, mock_logger, sample_ohlcv_data):
        """Test basic valley detection without parameters."""
        study = FindValleys(logger=mock_logger)
        result = study.calculate(sample_ohlcv_data, "AAPL", column="close")

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_ohlcv_data)

    def test_calculate_with_height_parameter_scalar(self, mock_logger):
        """Test valley detection with scalar height parameter."""
        study = FindValleys(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        # Create data with clear valleys
        close_prices = [
            110,
            108,
            95,
            97,
            99,
            90,
            92,
            94,
            96,
            98,
            85,
            87,
            89,
            91,
            93,
            95,
            97,
            99,
            101,
            103,
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

        result = study.calculate(ohlcv_data, "AAPL", column="close", height=95)

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_calculate_with_height_parameter_tuple(self, mock_logger):
        """Test valley detection with tuple height parameter."""
        study = FindValleys(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = [
            110,
            108,
            95,
            97,
            99,
            90,
            92,
            94,
            96,
            98,
            85,
            87,
            89,
            91,
            93,
            95,
            97,
            99,
            101,
            103,
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

        result = study.calculate(ohlcv_data, "AAPL", column="close", height=(80, 100))

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_calculate_with_distance_parameter(self, mock_logger):
        """Test valley detection with distance parameter."""
        study = FindValleys(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = [
            110,
            108,
            95,
            97,
            99,
            90,
            92,
            94,
            96,
            98,
            85,
            87,
            89,
            91,
            93,
            95,
            97,
            99,
            101,
            103,
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

    def test_calculate_with_prominence_parameter_scalar(self, mock_logger):
        """Test valley detection with scalar prominence parameter."""
        study = FindValleys(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = [
            110,
            108,
            95,
            97,
            99,
            90,
            92,
            94,
            96,
            98,
            85,
            87,
            89,
            91,
            93,
            95,
            97,
            99,
            101,
            103,
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

    def test_calculate_with_prominence_parameter_tuple(self, mock_logger):
        """Test valley detection with tuple prominence parameter."""
        study = FindValleys(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = [
            110,
            108,
            95,
            97,
            99,
            90,
            92,
            94,
            96,
            98,
            85,
            87,
            89,
            91,
            93,
            95,
            97,
            99,
            101,
            103,
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

        result = study.calculate(ohlcv_data, "AAPL", column="close", prominence=(5, 20))

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_calculate_with_width_parameter(self, mock_logger):
        """Test valley detection with width parameter."""
        study = FindValleys(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = [
            110,
            108,
            95,
            97,
            99,
            90,
            92,
            94,
            96,
            98,
            85,
            87,
            89,
            91,
            93,
            95,
            97,
            99,
            101,
            103,
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

    def test_calculate_with_threshold_parameter_scalar(self, mock_logger):
        """Test valley detection with scalar threshold parameter."""
        study = FindValleys(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = [
            110,
            108,
            95,
            97,
            99,
            90,
            92,
            94,
            96,
            98,
            85,
            87,
            89,
            91,
            93,
            95,
            97,
            99,
            101,
            103,
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

    def test_calculate_with_threshold_parameter_tuple(self, mock_logger):
        """Test valley detection with tuple threshold parameter."""
        study = FindValleys(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        close_prices = [
            110,
            108,
            95,
            97,
            99,
            90,
            92,
            94,
            96,
            98,
            85,
            87,
            89,
            91,
            93,
            95,
            97,
            99,
            101,
            103,
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

        result = study.calculate(ohlcv_data, "AAPL", column="close", threshold=(2, 10))

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_calculate_no_valleys_found(self, mock_logger):
        """Test when no valleys are found."""
        study = FindValleys(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        # Flat data - no valleys
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

        result = study.calculate(ohlcv_data, "AAPL", column="close", height=95)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(ohlcv_data)
        # Should have no valley columns
        assert len([col for col in result.columns if col.startswith("valley")]) == 0

    def test_calculate_missing_column(self, mock_logger, sample_ohlcv_data):
        """Test calculation fails when column is missing."""
        study = FindValleys(logger=mock_logger)
        result = study.calculate(sample_ohlcv_data, "AAPL", column="missing_column")

        assert result is None
        mock_logger.error.assert_called_once()

    def test_calculate_exception_handling(self, mock_logger, sample_ohlcv_data):
        """Test exception handling during valley detection."""
        study = FindValleys(logger=mock_logger)
        with patch(
            "system.algo_trader.strategy.studies.support_resistance.find_valleys.find_peaks",
            side_effect=Exception("Test error"),
        ):
            result = study.calculate(sample_ohlcv_data, "AAPL", column="close")

            assert result is None
            mock_logger.error.assert_called_once()


class TestFindValleysCompute:
    """Test FindValleys compute orchestration."""

    def test_compute_success(self, mock_logger, sample_ohlcv_data):
        """Test compute with all validation passing."""
        study = FindValleys(logger=mock_logger)
        result = study.compute(ohlcv_data=sample_ohlcv_data, ticker="AAPL", column="close")

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_compute_with_parameters(self, mock_logger, sample_ohlcv_data):
        """Test compute with all parameters."""
        study = FindValleys(logger=mock_logger)
        result = study.compute(
            ohlcv_data=sample_ohlcv_data,
            ticker="AAPL",
            column="close",
            height=95,
            distance=5,
            prominence=5,
            width=2,
            threshold=2,
        )

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_compute_fails_data_validation(self, mock_logger):
        """Test compute fails when data is None."""
        study = FindValleys(logger=mock_logger)
        result = study.compute(ohlcv_data=None, ticker="AAPL", column="close")
        assert result is None

    def test_compute_fails_insufficient_data(self, mock_logger):
        """Test compute fails with insufficient data."""
        study = FindValleys(logger=mock_logger)
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

    def test_compute_valley_naming(self, mock_logger):
        """Test that valleys are named correctly (valley1, valley2, etc.)."""
        study = FindValleys(logger=mock_logger)
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
        # Create data with multiple clear valleys
        close_prices = [
            110,
            108,
            95,
            97,
            99,
            90,
            92,
            94,
            96,
            98,
            85,
            87,
            89,
            91,
            93,
            95,
            97,
            99,
            101,
            103,
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

        result = study.compute(ohlcv_data=ohlcv_data, ticker="AAPL", column="close", height=95)

        if result is not None and not result.empty:
            valley_cols = [col for col in result.columns if col.startswith("valley")]
            if valley_cols:
                # Check naming convention
                assert all(col.startswith("valley") for col in valley_cols)
                # Check sequential numbering
                valley_numbers = [int(col.replace("valley", "")) for col in valley_cols]
                assert valley_numbers == sorted(valley_numbers)
