"""Unit tests for BaseStudy - Technical Indicator Study Base Class.

Tests cover validation methods, error handling, and abstract method enforcement.
All external dependencies are mocked to avoid logging calls.
"""

import pandas as pd
import pytest

from system.algo_trader.strategy.studies.base_study import BaseStudy


class ConcreteStudy(BaseStudy):
    """Concrete implementation of BaseStudy for testing."""

    def _validate_study_specific(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs) -> bool:
        """Test implementation of study-specific validation."""
        return kwargs.get("valid", True)

    def get_field_name(self, **params) -> str:
        """Test implementation of get_field_name."""
        # Simple test implementation - return a field name based on params
        param_str = "_".join(
            f"{k}_{v}"
            for k, v in sorted(params.items())
            if k not in {"valid", "column", "required_columns"}
        )
        return f"test_field_{param_str}" if param_str else "test_field"

    def calculate(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs) -> pd.Series | None:
        """Test implementation of calculation."""
        column = kwargs.get("column", "close")
        return ohlcv_data[column] * 2  # Simple test calculation


class TestBaseStudyInitialization:
    """Test BaseStudy initialization."""

    def test_initialization_with_logger(self, mock_logger):
        """Test initialization with provided logger."""
        study = ConcreteStudy(logger=mock_logger)
        assert study.logger == mock_logger

    def test_initialization_without_logger(self):
        """Test initialization without logger creates new one."""
        study = ConcreteStudy()
        assert study.logger is not None


class TestBaseStudyValidation:
    """Test BaseStudy validation methods."""

    def test_validate_data_with_valid_data(self, mock_logger, sample_ohlcv_data):
        """Test _validate_data with valid DataFrame."""
        study = ConcreteStudy(logger=mock_logger)
        result = study._validate_data(sample_ohlcv_data, "AAPL")
        assert result is True
        mock_logger.debug.assert_not_called()

    def test_validate_data_with_none(self, mock_logger):
        """Test _validate_data with None."""
        study = ConcreteStudy(logger=mock_logger)
        result = study._validate_data(None, "AAPL")
        assert result is False
        mock_logger.debug.assert_called_once()

    def test_validate_data_with_empty_dataframe(self, mock_logger, empty_ohlcv_data):
        """Test _validate_data with empty DataFrame."""
        study = ConcreteStudy(logger=mock_logger)
        result = study._validate_data(empty_ohlcv_data, "AAPL")
        assert result is False
        mock_logger.debug.assert_called_once()

    def test_validate_columns_with_all_columns(self, mock_logger, sample_ohlcv_data):
        """Test _validate_columns with all required columns present."""
        study = ConcreteStudy(logger=mock_logger)
        result = study._validate_columns(sample_ohlcv_data, ["close", "open"], "AAPL")
        assert result is True
        mock_logger.debug.assert_not_called()

    def test_validate_columns_with_missing_column(self, mock_logger, sample_ohlcv_data):
        """Test _validate_columns with missing column."""
        study = ConcreteStudy(logger=mock_logger)
        result = study._validate_columns(sample_ohlcv_data, ["close", "missing_col"], "AAPL")
        assert result is False
        mock_logger.debug.assert_called_once()

    def test_log_validation_error(self, mock_logger):
        """Test _log_validation_error logs correctly."""
        study = ConcreteStudy(logger=mock_logger)
        study._log_validation_error("AAPL", "Test error message")
        mock_logger.debug.assert_called_once_with("AAPL: Test error message")


class TestBaseStudyCompute:
    """Test BaseStudy compute orchestration."""

    def test_compute_success(self, mock_logger, sample_ohlcv_data):
        """Test compute with all validation passing."""
        study = ConcreteStudy(logger=mock_logger)
        result = study.compute(
            ohlcv_data=sample_ohlcv_data,
            ticker="AAPL",
            valid=True,
            required_columns=["close"],
            column="close",
        )
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv_data)

    def test_compute_fails_data_validation(self, mock_logger):
        """Test compute fails when data is None."""
        study = ConcreteStudy(logger=mock_logger)
        result = study.compute(ohlcv_data=None, ticker="AAPL", valid=True)
        assert result is None

    def test_compute_fails_column_validation(self, mock_logger, ohlcv_data_missing_close):
        """Test compute fails when required columns are missing."""
        study = ConcreteStudy(logger=mock_logger)
        result = study.compute(
            ohlcv_data=ohlcv_data_missing_close,
            ticker="AAPL",
            valid=True,
            required_columns=["close"],
        )
        assert result is None

    def test_compute_fails_study_specific_validation(self, mock_logger, sample_ohlcv_data):
        """Test compute fails when study-specific validation fails."""
        study = ConcreteStudy(logger=mock_logger)
        result = study.compute(
            ohlcv_data=sample_ohlcv_data,
            ticker="AAPL",
            valid=False,
            required_columns=["close"],
        )
        assert result is None

    def test_compute_validation_order(self, mock_logger, sample_ohlcv_data):
        """Test compute validates in correct order."""
        study = ConcreteStudy(logger=mock_logger)
        # This should pass all validations
        result = study.compute(
            ohlcv_data=sample_ohlcv_data,
            ticker="AAPL",
            valid=True,
            required_columns=["close"],
            column="close",
        )
        assert result is not None


class TestBaseStudyAbstractMethods:
    """Test BaseStudy abstract method enforcement."""

    def test_cannot_instantiate_base_study_directly(self):
        """Test that BaseStudy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseStudy()
