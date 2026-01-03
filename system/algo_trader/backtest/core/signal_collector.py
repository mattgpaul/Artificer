"""Signal collection for backtest execution.

This module provides functionality to collect trading signals from strategies
during backtest execution, handling time windowing and signal deduplication.
"""

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.utils.progress import ticker_progress_bar


class SignalCollector:
    """Collects trading signals from strategies during backtest execution.

    Handles time windowing, signal deduplication, and progress tracking for
    both single-ticker and multi-ticker backtest scenarios.

    Args:
        strategy: Strategy instance implementing buy() and sell() methods.
        logger: Optional logger instance. If None, creates a new logger.
        lookback_bars: Optional lookback window in bars. If None, uses strategy
            window or all available data.
    """

    def __init__(self, strategy, logger=None, lookback_bars: int | None = None) -> None:
        """Initialize SignalCollector with strategy and configuration.

        Args:
            strategy: Strategy instance implementing buy() and sell() methods.
            logger: Optional logger instance. If None, creates a new logger.
            lookback_bars: Optional lookback window in bars. If None, uses strategy
                window or all available data.
        """
        self.strategy = strategy
        self.logger = logger or get_logger(self.__class__.__name__)
        self.lookback_bars = lookback_bars

    def _normalize_timestamp(self, timestamp: pd.Timestamp) -> pd.Timestamp:
        if timestamp.tz is None:
            return pd.Timestamp(timestamp).tz_localize("UTC")
        return timestamp.tz_convert("UTC")

    def _normalize_index(self, data: pd.DataFrame) -> pd.DataFrame:
        if data is None or data.empty:
            return pd.DataFrame() if data is None else data
        result = data.copy()
        if result.index.tz is None:
            result.index = result.index.tz_localize("UTC")
        else:
            result.index = result.index.tz_convert("UTC")
        return result

    def _slice_window(self, data: pd.DataFrame, current_time: pd.Timestamp) -> pd.DataFrame:
        if data is None or data.empty:
            return pd.DataFrame() if data is None else data

        current_time_utc = self._normalize_timestamp(current_time)
        data_utc = self._normalize_index(data)
        visible = data_utc[data_utc.index <= current_time_utc]
        if visible.empty:
            return visible

        effective_lookback: int | None = None
        strategy_window = getattr(self.strategy, "window", None)
        if isinstance(strategy_window, int) and strategy_window > 0:
            effective_lookback = strategy_window
        elif self.lookback_bars is not None:
            effective_lookback = self.lookback_bars

        if effective_lookback is not None:
            return visible.tail(effective_lookback)
        return visible

    def _append_from_signals(
        self,
        signals: pd.DataFrame,
        ticker: str,
        signal_type: str,
        collected_keys: set,
        out: list,
    ) -> None:
        if signals is None or signals.empty:
            return

        df = signals.copy()
        if df.index.name != "signal_time":
            df.index.name = "signal_time"
        df["signal_time"] = pd.to_datetime(df.index, utc=True)
        df["ticker"] = ticker
        df["signal_type"] = signal_type

        for _, row in df.iterrows():
            ts = self._normalize_timestamp(row["signal_time"])
            price = float(row.get("price", 0.0))
            key = (ticker, ts, signal_type, price)
            if key in collected_keys:
                continue
            collected_keys.add(key)
            record = row.to_dict()
            record["signal_time"] = ts
            out.append(record)

    def collect_signals_for_ticker(
        self,
        ticker: str,
        step_intervals: pd.DatetimeIndex,
        data_cache: dict[str, pd.DataFrame],
    ) -> list:
        """Collect signals for a single ticker across all step intervals.

        Processes OHLCV data for a single ticker, executing the strategy at
        each step interval and collecting buy/sell signals. Includes progress
        tracking and error handling.

        Args:
            ticker: Ticker symbol to collect signals for.
            step_intervals: DatetimeIndex of time steps to evaluate strategy.
            data_cache: Dictionary mapping tickers to OHLCV DataFrames.

        Returns:
            List of signal dictionaries with keys: signal_time, ticker,
            signal_type, price, and any additional strategy-specific fields.
        """
        if ticker not in data_cache:
            return []

        ohlcv = data_cache[ticker]
        if ohlcv is None or ohlcv.empty:
            return []

        all_signals: list = []
        collected_keys: set = set()
        total_steps = len(step_intervals)

        with ticker_progress_bar(ticker, total_steps) as pbar:
            for idx, current_time in enumerate(step_intervals):
                window = self._slice_window(ohlcv, current_time)
                if window.empty:
                    if pbar is not None:
                        pbar.update(1)
                    continue

                try:
                    buy_signals = self.strategy.buy(window, ticker)
                    sell_signals = self.strategy.sell(window, ticker)
                    self._append_from_signals(
                        buy_signals,
                        ticker,
                        "buy",
                        collected_keys,
                        all_signals,
                    )
                    self._append_from_signals(
                        sell_signals,
                        ticker,
                        "sell",
                        collected_keys,
                        all_signals,
                    )
                except Exception as e:
                    msg = f"Error executing strategy for {ticker} at {current_time}: {e}"
                    if pbar is not None:
                        pbar.write(msg)
                    else:
                        self.logger.error(msg, exc_info=True)

                if pbar is not None:
                    pbar.update(1)
                    if idx % 10 == 0 or idx == total_steps - 1:
                        pbar.set_postfix({"signals": len(all_signals)})

        return all_signals

    def collect_signals_for_all_tickers(
        self,
        step_intervals: pd.DatetimeIndex,
        tickers: list[str],
        data_cache: dict[str, pd.DataFrame],
    ) -> list:
        """Collect signals for all tickers across all step intervals.

        Processes OHLCV data for multiple tickers, executing the strategy at
        each step interval for each ticker. Includes progress logging and
        error handling.

        Args:
            step_intervals: DatetimeIndex of time steps to evaluate strategy.
            tickers: List of ticker symbols to collect signals for.
            data_cache: Dictionary mapping tickers to OHLCV DataFrames.

        Returns:
            List of signal dictionaries with keys: signal_time, ticker,
            signal_type, price, and any additional strategy-specific fields.
        """
        all_signals: list = []
        collected_keys: set = set()

        for idx, current_time in enumerate(step_intervals):
            for ticker in tickers:
                if ticker not in data_cache:
                    continue
                ohlcv = data_cache[ticker]
                if ohlcv is None or ohlcv.empty:
                    continue

                window = self._slice_window(ohlcv, current_time)
                if window.empty:
                    continue

                try:
                    buy_signals = self.strategy.buy(window, ticker)
                    sell_signals = self.strategy.sell(window, ticker)
                    self._append_from_signals(
                        buy_signals,
                        ticker,
                        "buy",
                        collected_keys,
                        all_signals,
                    )
                    self._append_from_signals(
                        sell_signals,
                        ticker,
                        "sell",
                        collected_keys,
                        all_signals,
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error executing strategy for {ticker} at {current_time}: {e}"
                    )

            if (idx + 1) % max(1, len(step_intervals) // 10) == 0 or idx == len(step_intervals) - 1:
                progress_pct = ((idx + 1) / len(step_intervals)) * 100
                self.logger.info(
                    f"Backtest progress: {progress_pct:.0f}% "
                    f"({idx + 1}/{len(step_intervals)} steps, "
                    f"{len(all_signals)} signals collected)"
                )

        return all_signals
