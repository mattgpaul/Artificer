"""Core filter types and pipeline implementation.

This module defines the Filter protocol, FilterContext for passing data to filters,
and FilterPipeline for chaining multiple filters together.
"""

from typing import Any, Protocol

import pandas as pd

from infrastructure.logging.logger import get_logger


class FilterContext:
    """Context object passed to filters during evaluation.

    Contains the signal being evaluated and optional OHLCV data for tickers.
    """

    def __init__(
        self,
        signal: dict[str, Any],
        ohlcv_by_ticker: dict[str, pd.DataFrame] | None = None,
    ):
        """Initialize filter context.

        Args:
            signal: Dictionary containing signal data to evaluate.
            ohlcv_by_ticker: Optional dictionary mapping ticker symbols to OHLCV DataFrames.
        """
        self.signal = signal
        self.ohlcv_by_ticker = ohlcv_by_ticker or {}

    def get_ticker_ohlcv(self, ticker: str) -> pd.DataFrame | None:
        """Get OHLCV data for a specific ticker.

        Args:
            ticker: Ticker symbol to look up.

        Returns:
            DataFrame containing OHLCV data, or None if not found.
        """
        return self.ohlcv_by_ticker.get(ticker)


class Filter(Protocol):
    """Protocol defining the interface for filter implementations."""

    def evaluate(self, context: FilterContext) -> bool:
        """Evaluate whether a signal passes the filter.

        Args:
            context: FilterContext containing signal and OHLCV data.

        Returns:
            True if signal passes filter, False otherwise.
        """
        pass


class FilterPipeline:
    """Pipeline for chaining multiple filters together."""

    def __init__(self, filters: list[Filter], logger=None):
        """Initialize filter pipeline.

        Args:
            filters: List of Filter instances to apply in sequence.
            logger: Optional logger instance.
        """
        self.filters = filters
        self.logger = logger or get_logger(self.__class__.__name__)

    def is_valid(
        self, signal: dict[str, Any], ohlcv_by_ticker: dict[str, pd.DataFrame] | None = None
    ) -> bool:
        """Check if a signal passes all filters in the pipeline.

        Args:
            signal: Dictionary containing signal data to evaluate.
            ohlcv_by_ticker: Optional dictionary mapping ticker symbols to OHLCV DataFrames.

        Returns:
            True if signal passes all filters, False otherwise.
        """
        context = FilterContext(signal, ohlcv_by_ticker)
        for filter_instance in self.filters:
            try:
                if not filter_instance.evaluate(context):
                    ticker = signal.get("ticker", "unknown")
                    signal_time = signal.get("signal_time", "unknown")
                    self.logger.debug(
                        f"Filter {filter_instance.__class__.__name__} rejected signal "
                        f"for {ticker} at {signal_time}"
                    )
                    return False
            except Exception as e:
                ticker = signal.get("ticker", "unknown")
                signal_time = signal.get("signal_time", "unknown")
                self.logger.warning(
                    f"Filter {filter_instance.__class__.__name__} raised exception "
                    f"for {ticker} at {signal_time}: {e}"
                )
                return False
        return True

    def apply(
        self, signals: pd.DataFrame, ohlcv_by_ticker: dict[str, pd.DataFrame] | None = None
    ) -> pd.DataFrame:
        """Apply filter pipeline to a DataFrame of signals.

        Args:
            signals: DataFrame containing signals to filter.
            ohlcv_by_ticker: Optional dictionary mapping ticker symbols to OHLCV DataFrames.

        Returns:
            DataFrame containing only signals that passed all filters.
        """
        if signals.empty:
            return signals

        if not self.filters:
            return signals

        filtered_indices = []
        for idx, signal_row in signals.iterrows():
            signal_dict = signal_row.to_dict()
            if self.is_valid(signal_dict, ohlcv_by_ticker):
                filtered_indices.append(idx)

        if not filtered_indices:
            return pd.DataFrame()

        return signals.loc[filtered_indices]
