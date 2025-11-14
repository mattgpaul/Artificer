"""Signal collector for backtest execution.

This module provides functionality to collect trading signals from strategy execution
during backtesting, handling timezone normalization and duplicate signal detection.
"""

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.utils.progress import ticker_progress_bar
from system.algo_trader.backtest.utils.strategy_wrapper import BacktestStrategyWrapper


class SignalCollector:
    """Collects trading signals during backtest execution.

    This class manages signal collection from strategy execution, ensuring proper
    timezone handling and preventing duplicate signals from being collected.

    Args:
        strategy: Strategy instance to collect signals from.
        logger: Optional logger instance. If not provided, creates a new logger.
    """

    def __init__(self, strategy, logger=None):
        """Initialize SignalCollector with strategy.

        Args:
            strategy: Strategy instance to collect signals from.
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        self.strategy = strategy
        self.logger = logger or get_logger(self.__class__.__name__)

    def normalize_timezone(self, timestamp: pd.Timestamp) -> pd.Timestamp:
        """Normalize timestamp to UTC timezone.

        Converts a timestamp to UTC, localizing if timezone-naive or converting
        if timezone-aware.

        Args:
            timestamp: Timestamp to normalize.

        Returns:
            Timestamp with UTC timezone.
        """
        if timestamp.tz is None:
            return pd.Timestamp(timestamp).tz_localize("UTC")
        return timestamp.tz_convert("UTC")

    def normalize_signal_timezone(self, signals: pd.DataFrame) -> pd.DataFrame:
        """Normalize signal_time column to UTC timezone.

        Ensures all signal times in the DataFrame are timezone-aware and in UTC.

        Args:
            signals: DataFrame with signal_time column to normalize.

        Returns:
            DataFrame with normalized signal_time column in UTC.
        """
        signals["signal_time"] = pd.to_datetime(signals["signal_time"], utc=True)
        if signals["signal_time"].dt.tz is None:
            signals["signal_time"] = signals["signal_time"].dt.tz_localize("UTC")
        else:
            signals["signal_time"] = signals["signal_time"].dt.tz_convert("UTC")
        return signals

    def create_signal_key(
        self, ticker: str, signal_time: pd.Timestamp, signal_type: str, price: float
    ) -> tuple:
        """Create a unique key for a signal to detect duplicates.

        Args:
            ticker: Ticker symbol.
            signal_time: Timestamp of the signal.
            signal_type: Type of signal (e.g., 'BUY', 'SELL').
            price: Price associated with the signal.

        Returns:
            Tuple containing (ticker, signal_time, signal_type, price) for deduplication.
        """
        return (ticker, signal_time, signal_type, float(price))

    def process_signals_for_time_step(
        self,
        signals: pd.DataFrame,
        ticker: str,
        current_time: pd.Timestamp,
        collected_signal_keys: set,
        last_collection_time: pd.Timestamp | None,
    ) -> tuple[list, pd.Timestamp | None]:
        """Process signals for a single time step.

        Filters signals that occur at or before the current time step and after
        the last collection time, preventing duplicate collection.

        Args:
            signals: DataFrame containing all signals for the ticker.
            ticker: Ticker symbol being processed.
            current_time: Current time step being processed.
            collected_signal_keys: Set of signal keys already collected.
            last_collection_time: Timestamp of last signal collection, or None.

        Returns:
            Tuple of (new_signals_list, updated_last_collection_time).
        """
        if signals.empty:
            return [], last_collection_time or current_time

        signals = self.normalize_signal_timezone(signals)
        current_time_normalized = self.normalize_timezone(current_time)

        mask = signals["signal_time"] <= current_time_normalized
        if last_collection_time is not None:
            mask = mask & (signals["signal_time"] > last_collection_time)

        current_step_signals = signals[mask]
        new_signals = []

        for _, signal in current_step_signals.iterrows():
            signal_time_val = signal["signal_time"]
            signal_time_normalized = self.normalize_timezone(signal_time_val)

            signal_key = self.create_signal_key(
                ticker=ticker,
                signal_time=signal_time_normalized,
                signal_type=signal["signal_type"],
                price=signal.get("price", 0),
            )

            if signal_key not in collected_signal_keys:
                collected_signal_keys.add(signal_key)
                new_signals.append(signal.to_dict())

        if not current_step_signals.empty:
            max_signal_time = current_step_signals["signal_time"].max()
            if last_collection_time is None or max_signal_time > last_collection_time:
                last_collection_time = max_signal_time
        elif last_collection_time is None:
            last_collection_time = current_time_normalized

        return new_signals, last_collection_time

    def process_signals_for_ticker_at_time(
        self,
        signals: pd.DataFrame,
        ticker: str,
        current_time: pd.Timestamp,
        collected_signal_keys: set,
        last_collection_time: dict[str, pd.Timestamp],
    ) -> tuple[list, dict[str, pd.Timestamp]]:
        """Process signals for a ticker at a specific time step.

        Similar to process_signals_for_time_step but maintains per-ticker
        collection times for multi-ticker backtests.

        Args:
            signals: DataFrame containing all signals for the ticker.
            ticker: Ticker symbol being processed.
            current_time: Current time step being processed.
            collected_signal_keys: Set of signal keys already collected.
            last_collection_time: Dictionary mapping tickers to last collection times.

        Returns:
            Tuple of (new_signals_list, updated_last_collection_time_dict).
        """
        if signals.empty:
            return [], last_collection_time

        signals = self.normalize_signal_timezone(signals)
        current_time_normalized = self.normalize_timezone(current_time)

        mask = signals["signal_time"] <= current_time_normalized
        if ticker in last_collection_time:
            mask = mask & (signals["signal_time"] > last_collection_time[ticker])

        current_step_signals = signals[mask]
        new_signals = []

        for _, signal in current_step_signals.iterrows():
            signal_time_val = signal["signal_time"]
            signal_time_normalized = self.normalize_timezone(signal_time_val)

            signal_key = self.create_signal_key(
                ticker=ticker,
                signal_time=signal_time_normalized,
                signal_type=signal["signal_type"],
                price=signal.get("price", 0),
            )

            if signal_key not in collected_signal_keys:
                collected_signal_keys.add(signal_key)
                new_signals.append(signal.to_dict())

        if not current_step_signals.empty:
            max_signal_time = current_step_signals["signal_time"].max()
            if ticker not in last_collection_time or max_signal_time > last_collection_time[ticker]:
                last_collection_time[ticker] = max_signal_time
        elif ticker not in last_collection_time:
            last_collection_time[ticker] = current_time_normalized

        return new_signals, last_collection_time

    def collect_signals_for_ticker(
        self,
        ticker: str,
        step_intervals: pd.DatetimeIndex,
        data_cache: dict[str, pd.DataFrame],
    ) -> list:
        """Collect all signals for a single ticker across time steps.

        Executes the strategy at each time step and collects unique signals,
        displaying progress with a progress bar.

        Args:
            ticker: Ticker symbol to collect signals for.
            step_intervals: DatetimeIndex of time steps to process.
            data_cache: Dictionary mapping ticker symbols to OHLCV DataFrames.

        Returns:
            List of signal dictionaries collected during backtest execution.
        """
        wrapper = BacktestStrategyWrapper(self.strategy, step_intervals[0], data_cache)
        original_query_ohlcv = self.strategy.query_ohlcv
        self.strategy.query_ohlcv = wrapper.query_ohlcv

        all_signals = []
        collected_signal_keys = set()
        last_collection_time: pd.Timestamp | None = None
        total_steps = len(step_intervals)

        try:
            with ticker_progress_bar(ticker, total_steps) as pbar:
                for idx, current_time in enumerate(step_intervals):
                    wrapper.current_time = current_time

                    try:
                        signals = self.strategy.run_strategy(ticker=ticker, write_signals=False)
                        new_signals, last_collection_time = self.process_signals_for_time_step(
                            signals=signals,
                            ticker=ticker,
                            current_time=current_time,
                            collected_signal_keys=collected_signal_keys,
                            last_collection_time=last_collection_time,
                        )
                        all_signals.extend(new_signals)

                    except Exception as e:
                        error_msg = f"Error executing strategy for {ticker} at {current_time}: {e}"
                        if pbar is not None:
                            pbar.write(error_msg)
                        else:
                            self.logger.error(error_msg, exc_info=True)

                    if pbar is not None:
                        pbar.update(1)
                        if idx % 10 == 0 or idx == total_steps - 1:
                            pbar.set_postfix({"signals": len(all_signals)})
        finally:
            self.strategy.query_ohlcv = original_query_ohlcv

        return all_signals

    def collect_signals_for_all_tickers(
        self,
        step_intervals: pd.DatetimeIndex,
        tickers: list[str],
        data_cache: dict[str, pd.DataFrame],
    ) -> list:
        """Collect signals for multiple tickers across time steps.

        Executes the strategy for all tickers at each time step and collects
        unique signals, logging progress periodically.

        Args:
            step_intervals: DatetimeIndex of time steps to process.
            tickers: List of ticker symbols to collect signals for.
            data_cache: Dictionary mapping ticker symbols to OHLCV DataFrames.

        Returns:
            List of signal dictionaries collected during backtest execution.
        """
        wrapper = BacktestStrategyWrapper(self.strategy, step_intervals[0], data_cache)
        original_query_ohlcv = self.strategy.query_ohlcv
        self.strategy.query_ohlcv = wrapper.query_ohlcv

        all_signals = []
        collected_signal_keys = set()
        last_collection_time: dict[str, pd.Timestamp] = {}

        try:
            for idx, current_time in enumerate(step_intervals):
                wrapper.current_time = current_time

                for ticker in tickers:
                    if ticker not in data_cache:
                        continue

                    try:
                        signals = self.strategy.run_strategy(ticker=ticker, write_signals=False)
                        new_signals, last_collection_time = self.process_signals_for_ticker_at_time(
                            signals=signals,
                            ticker=ticker,
                            current_time=current_time,
                            collected_signal_keys=collected_signal_keys,
                            last_collection_time=last_collection_time,
                        )
                        all_signals.extend(new_signals)

                    except Exception as e:
                        self.logger.error(
                            f"Error executing strategy for {ticker} at {current_time}: {e}"
                        )

                if (idx + 1) % max(1, len(step_intervals) // 10) == 0 or idx == len(
                    step_intervals
                ) - 1:
                    progress_pct = ((idx + 1) / len(step_intervals)) * 100
                    self.logger.info(
                        f"Backtest progress: {progress_pct:.0f}% "
                        f"({idx + 1}/{len(step_intervals)} steps, "
                        f"{len(all_signals)} signals collected)"
                    )
        finally:
            self.strategy.query_ohlcv = original_query_ohlcv

        return all_signals
