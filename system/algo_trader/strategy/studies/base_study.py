"""Base class for technical indicator studies.

This module provides the BaseStudy abstract base class that handles common
validation logic (data existence, column checks, logging) for all technical
indicator studies. Individual studies inherit from this class and implement
study-specific validation and calculation logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import pandas as pd

from infrastructure.logging.logger import get_logger


@dataclass
class StudySpec:
    """Specification for a technical study (indicator) to be computed.

    This dataclass defines the configuration for a single technical study
    that will be computed during strategy execution. It includes the study
    instance, parameters, and minimum data requirements.

    Attributes:
        name: Unique name identifier for this study (e.g., "sma_short").
        study: BaseStudy instance that will perform the calculation.
        params: Dictionary of parameters to pass to the study's compute method.
        min_bars: Minimum number of bars required before study can be computed.
            None means no minimum requirement.
    """

    name: str
    study: "BaseStudy"
    params: dict[str, Any]
    min_bars: int | None = None


class BaseStudy(ABC):
    """Abstract base class for technical indicator studies.

    Provides common validation methods that all studies need:
    - Data existence checks (None/empty)
    - Required column validation
    - Consistent error logging

    Subclasses must implement:
    - `_validate_study_specific()`: Study-specific validation logic
    - `calculate()`: The actual calculation logic

    Attributes:
        logger: Logger instance for validation and error messages.
    """

    def __init__(self, logger=None):
        """Initialize BaseStudy with optional logger.

        Args:
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        self.logger = logger or get_logger(self.__class__.__name__)

    def _validate_data(self, ohlcv_data: pd.DataFrame | None, ticker: str) -> bool:
        """Validate that OHLCV data exists and is not empty.

        Args:
            ohlcv_data: DataFrame with OHLCV data to validate.
            ticker: Stock ticker symbol (for logging purposes).

        Returns:
            True if data is valid (not None and not empty), False otherwise.
        """
        if ohlcv_data is None or ohlcv_data.empty:
            self._log_validation_error(ticker, "No OHLCV data provided")
            return False
        return True

    def _validate_columns(
        self, ohlcv_data: pd.DataFrame, required_columns: list[str], ticker: str
    ) -> bool:
        """Validate that required columns exist in OHLCV data.

        Args:
            ohlcv_data: DataFrame with OHLCV data to validate.
            required_columns: List of required column names.
            ticker: Stock ticker symbol (for logging purposes).

        Returns:
            True if all required columns exist, False otherwise.
        """
        missing_columns = [col for col in required_columns if col not in ohlcv_data.columns]
        if missing_columns:
            self._log_validation_error(
                ticker, f"OHLCV data missing required columns: {missing_columns}"
            )
            return False
        return True

    def _log_validation_error(self, ticker: str, message: str) -> None:
        """Log validation error with consistent format.

        Args:
            ticker: Stock ticker symbol.
            message: Error message to log.
        """
        self.logger.debug(f"{ticker}: {message}")

    @abstractmethod
    def _validate_study_specific(
        self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs: Any
    ) -> bool:
        """Validate study-specific requirements.

        Subclasses must implement this method to check study-specific
        validation requirements (e.g., minimum data length, parameter ranges).

        Args:
            ohlcv_data: DataFrame with OHLCV data to validate.
            ticker: Stock ticker symbol (for logging purposes).
            **kwargs: Study-specific parameters for validation.

        Returns:
            True if study-specific validation passes, False otherwise.
        """
        pass

    @abstractmethod
    def calculate(self, ohlcv_data: pd.DataFrame, ticker: str, **kwargs: Any) -> pd.Series | None:
        """Perform the actual calculation for this study.

        Subclasses must implement this method to perform the technical
        indicator calculation. This method is called after all validation
        has passed.

        Args:
            ohlcv_data: DataFrame with OHLCV data (already validated).
            ticker: Stock ticker symbol (for logging purposes).
            **kwargs: Study-specific parameters for calculation.

        Returns:
            Series with calculated values, or None if calculation fails.
            Series may contain NaN values for insufficient data periods.
        """
        pass

    def compute(
        self, ohlcv_data: pd.DataFrame | None, ticker: str, **kwargs: Any
    ) -> pd.Series | None:
        """Orchestrate validation and calculation.

        This is the main public method that subclasses expose. It performs
        all validation checks in order, then calls the calculation method
        if validation passes.

        Validation order:
        1. Data existence check
        2. Required columns check
        3. Study-specific validation

        Args:
            ohlcv_data: DataFrame with OHLCV data to process.
            ticker: Stock ticker symbol (for logging purposes).
            **kwargs: Study-specific parameters passed to validation and calculation.

        Returns:
            Series with calculated values if all validation passes, None otherwise.
        """
        # Step 1: Validate data exists
        if not self._validate_data(ohlcv_data, ticker):
            return None

        # Step 2: Validate required columns (subclasses should specify in kwargs or override)
        required_columns = kwargs.get("required_columns", ["close"])
        if not self._validate_columns(ohlcv_data, required_columns, ticker):
            return None

        # Step 3: Validate study-specific requirements
        if not self._validate_study_specific(ohlcv_data, ticker, **kwargs):
            return None

        # Step 4: Perform calculation
        return self.calculate(ohlcv_data, ticker, **kwargs)
