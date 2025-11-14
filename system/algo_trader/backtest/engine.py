"""Backtesting engine for trading strategies.

This module provides the core backtesting functionality, including:
- BacktestEngine: Main engine for running backtests
- BacktestResults: Container for backtest results
"""

from typing import TYPE_CHECKING

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.execution import ExecutionConfig, ExecutionSimulator
from system.algo_trader.backtest.progress import ticker_progress_bar
from system.algo_trader.backtest.strategy_wrapper import BacktestStrategyWrapper
from system.algo_trader.influx.market_data_influx import MarketDataInflux
from system.algo_trader.strategy.journal import TradeJournal

if TYPE_CHECKING:
    from system.algo_trader.strategy.base import BaseStrategy


class BacktestResults:
    """Container for backtest results.

    Attributes:
        signals: DataFrame containing trading signals.
        trades: DataFrame containing executed trades.
        metrics: Dictionary containing performance metrics.
        strategy_name: Name of the strategy used.
    """

    def __init__(self) -> None:
        """Initialize empty BacktestResults."""
        self.signals: pd.DataFrame = pd.DataFrame()
        self.trades: pd.DataFrame = pd.DataFrame()
        self.metrics: dict = {}
        self.strategy_name: str = ""


class BacktestEngine:
    """Main engine for running backtests on trading strategies.

    The BacktestEngine executes strategies against historical data, simulating
    real-time trading conditions while preventing forward-looking bias.

    Args:
        strategy: Strategy instance to backtest.
        tickers: List of ticker symbols to backtest.
        start_date: Start date for the backtest period.
        end_date: End date for the backtest period.
        step_frequency: Time-stepping frequency (e.g., 'daily', 'hourly').
        database: InfluxDB database name for OHLCV data.
        execution_config: Execution simulation configuration.
        capital_per_trade: Capital allocated per trade.
        risk_free_rate: Risk-free rate for performance calculations.
    """

    def __init__(
        self,
        strategy: "BaseStrategy",
        tickers: list[str],
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        step_frequency: str,
        database: str = "algo-trader-ohlcv",
        execution_config: ExecutionConfig | None = None,
        capital_per_trade: float = 10000.0,
        risk_free_rate: float = 0.04,
    ) -> None:
        """Initialize BacktestEngine with strategy and configuration.

        Args:
            strategy: Strategy instance to backtest.
            tickers: List of ticker symbols to backtest.
            start_date: Start date for the backtest period.
            end_date: End date for the backtest period.
            step_frequency: Time-stepping frequency (e.g., 'daily', 'hourly').
            database: InfluxDB database name for OHLCV data.
            execution_config: Execution simulation configuration.
            capital_per_trade: Capital allocated per trade.
            risk_free_rate: Risk-free rate for performance calculations.
        """
        self.strategy = strategy
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.step_frequency = step_frequency
        self.database = database
        self.execution_config = execution_config or ExecutionConfig()
        self.capital_per_trade = capital_per_trade
        self.risk_free_rate = risk_free_rate
        self.logger = get_logger(self.__class__.__name__)

        self.influx_client = MarketDataInflux(database=database)
        self.data_cache: dict[str, pd.DataFrame] = {}
        self.execution_simulator = ExecutionSimulator(self.execution_config)

    def _load_ohlcv_data(self) -> None:
        self.logger.info(f"Loading OHLCV data for {len(self.tickers)} tickers")
        start_str = self.start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = self.end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        for ticker in self.tickers:
            query = (
                f"SELECT * FROM ohlcv WHERE ticker = '{ticker}' "
                f"AND time >= '{start_str}' AND time <= '{end_str}' "
                f"ORDER BY time ASC"
            )
            df = self.influx_client.query(query)

            if df is None or (isinstance(df, bool) and not df) or df.empty:
                self.logger.warning(f"No OHLCV data found for {ticker}")
                continue

            if "time" in df.columns:
                df["time"] = pd.to_datetime(df["time"], utc=True)
                df = df.set_index("time")
                # Ensure index is timezone-aware (UTC)
                if df.index.tz is None:
                    df.index = df.index.tz_localize("UTC")
                else:
                    df.index = df.index.tz_convert("UTC")

            self.data_cache[ticker] = df
            self.logger.debug(f"Loaded {len(df)} records for {ticker}")

    def _load_ticker_ohlcv_data(self, ticker: str) -> pd.DataFrame | None:
        start_str = self.start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = self.end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        query = (
            f"SELECT * FROM ohlcv WHERE ticker = '{ticker}' "
            f"AND time >= '{start_str}' AND time <= '{end_str}' "
            f"ORDER BY time ASC"
        )
        df = self.influx_client.query(query)

        if df is None or (isinstance(df, bool) and not df) or df.empty:
            self.logger.warning(f"No OHLCV data found for {ticker}")
            return None

        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], utc=True)
            df = df.set_index("time")
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
            else:
                df.index = df.index.tz_convert("UTC")

        self.logger.debug(f"Loaded {len(df)} records for {ticker}")
        return df

    def _determine_step_intervals(self) -> pd.DatetimeIndex:
        if self.step_frequency == "auto":
            if not self.data_cache:
                return pd.DatetimeIndex([])

            all_timestamps = []
            for df in self.data_cache.values():
                all_timestamps.extend(df.index.tolist())

            if not all_timestamps:
                return pd.DatetimeIndex([])

            timestamps_series = pd.Series(all_timestamps).sort_values()
            diffs = timestamps_series.diff().dropna()
            most_common_diff = diffs.mode()[0] if not diffs.empty else pd.Timedelta(days=1)

            freq_str = self._timedelta_to_freq(most_common_diff)
            self.logger.info(f"Auto-detected step frequency: {freq_str}")

        elif self.step_frequency == "daily":
            freq_str = "D"
        elif self.step_frequency == "hourly":
            freq_str = "H"
        elif self.step_frequency == "minute":
            freq_str = "T"
        else:
            freq_str = self.step_frequency

        try:
            intervals = pd.date_range(
                start=self.start_date, end=self.end_date, freq=freq_str, tz="UTC"
            )
            return intervals
        except Exception as e:
            self.logger.error(f"Invalid frequency '{freq_str}': {e}")
            return pd.date_range(start=self.start_date, end=self.end_date, freq="D", tz="UTC")

    def _timedelta_to_freq(self, td: pd.Timedelta) -> str:
        if td >= pd.Timedelta(days=1):
            return "D"
        elif td >= pd.Timedelta(hours=1):
            return "H"
        elif td >= pd.Timedelta(minutes=1):
            return "T"
        else:
            return "S"

    def _normalize_timezone(self, timestamp: pd.Timestamp) -> pd.Timestamp:
        """Normalize timestamp to UTC timezone.

        Args:
            timestamp: Timestamp to normalize.

        Returns:
            UTC timezone-aware timestamp.
        """
        if timestamp.tz is None:
            return pd.Timestamp(timestamp).tz_localize("UTC")
        return timestamp.tz_convert("UTC")

    def _normalize_signal_timezone(self, signals: pd.DataFrame) -> pd.DataFrame:
        """Normalize signal_time column to UTC timezone.

        Args:
            signals: DataFrame with signal_time column.

        Returns:
            DataFrame with normalized signal_time.
        """
        signals["signal_time"] = pd.to_datetime(signals["signal_time"], utc=True)
        if signals["signal_time"].dt.tz is None:
            signals["signal_time"] = signals["signal_time"].dt.tz_localize("UTC")
        else:
            signals["signal_time"] = signals["signal_time"].dt.tz_convert("UTC")
        return signals

    def _create_signal_key(
        self, ticker: str, signal_time: pd.Timestamp, signal_type: str, price: float
    ) -> tuple:
        """Create unique signal key for deduplication.

        Args:
            ticker: Ticker symbol.
            signal_time: Signal timestamp.
            signal_type: Signal type.
            price: Signal price.

        Returns:
            Tuple representing unique signal key.
        """
        return (ticker, signal_time, signal_type, float(price))

    def _process_signals_for_time_step(
        self,
        signals: pd.DataFrame,
        ticker: str,
        current_time: pd.Timestamp,
        collected_signal_keys: set,
        last_collection_time: pd.Timestamp | None,
    ) -> tuple[list, pd.Timestamp | None]:
        """Process signals for a single time step.

        Args:
            signals: DataFrame of signals from strategy.
            ticker: Ticker symbol.
            current_time: Current time step timestamp.
            collected_signal_keys: Set of already collected signal keys.
            last_collection_time: Last time signals were collected.

        Returns:
            Tuple of (new_signals_list, updated_last_collection_time).
        """
        if signals.empty:
            return [], last_collection_time or current_time

        signals = self._normalize_signal_timezone(signals)
        current_time_normalized = self._normalize_timezone(current_time)

        # Filter signals: only collect signals at or before current_time
        mask = signals["signal_time"] <= current_time_normalized
        if last_collection_time is not None:
            mask = mask & (signals["signal_time"] > last_collection_time)

        current_step_signals = signals[mask]
        new_signals = []

        for _, signal in current_step_signals.iterrows():
            signal_time_val = signal["signal_time"]
            signal_time_normalized = self._normalize_timezone(signal_time_val)

            signal_key = self._create_signal_key(
                ticker=ticker,
                signal_time=signal_time_normalized,
                signal_type=signal["signal_type"],
                price=signal.get("price", 0),
            )

            if signal_key not in collected_signal_keys:
                collected_signal_keys.add(signal_key)
                new_signals.append(signal.to_dict())

        # Update last collection time
        if not current_step_signals.empty:
            max_signal_time = current_step_signals["signal_time"].max()
            if last_collection_time is None or max_signal_time > last_collection_time:
                last_collection_time = max_signal_time
        elif last_collection_time is None:
            last_collection_time = current_time_normalized

        return new_signals, last_collection_time

    def _process_signals_for_ticker_at_time(
        self,
        signals: pd.DataFrame,
        ticker: str,
        current_time: pd.Timestamp,
        collected_signal_keys: set,
        last_collection_time: dict[str, pd.Timestamp],
    ) -> tuple[list, dict[str, pd.Timestamp]]:
        """Process signals for a ticker at a specific time step (multi-ticker mode).

        Args:
            signals: DataFrame of signals from strategy.
            ticker: Ticker symbol.
            current_time: Current time step timestamp.
            collected_signal_keys: Set of already collected signal keys.
            last_collection_time: Dictionary mapping tickers to last collection time.

        Returns:
            Tuple of (new_signals_list, updated_last_collection_time_dict).
        """
        if signals.empty:
            return [], last_collection_time

        signals = self._normalize_signal_timezone(signals)
        current_time_normalized = self._normalize_timezone(current_time)

        # Filter signals: only collect signals at or before current_time
        mask = signals["signal_time"] <= current_time_normalized
        if ticker in last_collection_time:
            mask = mask & (signals["signal_time"] > last_collection_time[ticker])

        current_step_signals = signals[mask]
        new_signals = []

        for _, signal in current_step_signals.iterrows():
            signal_time_val = signal["signal_time"]
            signal_time_normalized = self._normalize_timezone(signal_time_val)

            signal_key = self._create_signal_key(
                ticker=ticker,
                signal_time=signal_time_normalized,
                signal_type=signal["signal_type"],
                price=signal.get("price", 0),
            )

            if signal_key not in collected_signal_keys:
                collected_signal_keys.add(signal_key)
                new_signals.append(signal.to_dict())

        # Update last collection time for this ticker
        if not current_step_signals.empty:
            max_signal_time = current_step_signals["signal_time"].max()
            if ticker not in last_collection_time or max_signal_time > last_collection_time[ticker]:
                last_collection_time[ticker] = max_signal_time
        elif ticker not in last_collection_time:
            last_collection_time[ticker] = current_time_normalized

        return new_signals, last_collection_time

    def _generate_results_from_signals(
        self, signals: pd.DataFrame, ticker: str, ticker_data: pd.DataFrame
    ) -> BacktestResults:
        """Generate BacktestResults from collected signals.

        Args:
            signals: DataFrame of collected signals.
            ticker: Ticker symbol.
            ticker_data: OHLCV data for the ticker.

        Returns:
            BacktestResults with signals, trades, and metrics.
        """
        results = BacktestResults()
        results.signals = signals
        results.strategy_name = self.strategy.strategy_name

        journal = TradeJournal(
            signals=signals,
            strategy_name=self.strategy.strategy_name,
            ohlcv_data=ticker_data,
            capital_per_trade=self.capital_per_trade,
            risk_free_rate=self.risk_free_rate,
        )

        metrics, trades = journal.generate_report()
        results.metrics = metrics

        if not trades.empty:
            data_cache = {ticker: ticker_data}
            executed_trades = self.execution_simulator.apply_execution(trades, data_cache)
            results.trades = executed_trades

        return results

    def run_ticker(self, ticker: str) -> BacktestResults:
        """Run backtest for a single ticker.

        Args:
            ticker: Ticker symbol to backtest.

        Returns:
            BacktestResults containing signals, trades, and metrics.
        """
        ticker_data = self._load_ticker_ohlcv_data(ticker)
        if ticker_data is None or ticker_data.empty:
            self.logger.warning(
                f"{ticker}: No OHLCV data found in date range "
                f"{self.start_date.date()} to {self.end_date.date()}"
            )
            return BacktestResults()

        self.logger.debug(f"{ticker}: Loaded {len(ticker_data)} OHLCV records")

        data_cache = {ticker: ticker_data}
        step_intervals = self._determine_step_intervals_for_data(data_cache)
        if len(step_intervals) == 0:
            self.logger.warning(f"No time steps determined for {ticker}")
            return BacktestResults()

        all_signals = self._collect_signals_for_ticker(ticker, step_intervals, data_cache)

        if not all_signals:
            self.logger.debug(
                f"{ticker}: No signals generated "
                "(insufficient data for SMA crossover or no crossovers detected)"
            )
            return BacktestResults()

        combined_signals = pd.DataFrame(all_signals).sort_values("signal_time")
        self.logger.debug(f"{ticker}: Generated {len(combined_signals)} unique signals")

        return self._generate_results_from_signals(combined_signals, ticker, ticker_data)

    def _collect_signals_for_ticker(
        self,
        ticker: str,
        step_intervals: pd.DatetimeIndex,
        data_cache: dict[str, pd.DataFrame],
    ) -> list:
        """Collect signals for a ticker across all time steps.

        Args:
            ticker: Ticker symbol.
            step_intervals: Time step intervals to process.
            data_cache: Dictionary of ticker data.

        Returns:
            List of signal dictionaries.
        """
        # SEQUENTIAL EXECUTION: Call run_strategy for each time step to ensure
        # no forward-looking bias. At each step, the wrapper filters data to
        # only show data <= current_time, ensuring the strategy only sees
        # historical data up to that point. This simulates how the strategy
        # would run in real-time.
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
                        new_signals, last_collection_time = self._process_signals_for_time_step(
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

    def _determine_step_intervals_for_data(
        self, data_cache: dict[str, pd.DataFrame]
    ) -> pd.DatetimeIndex:
        if self.step_frequency == "auto":
            if not data_cache:
                return pd.DatetimeIndex([])

            all_timestamps = []
            for df in data_cache.values():
                all_timestamps.extend(df.index.tolist())

            if not all_timestamps:
                return pd.DatetimeIndex([])

            timestamps_series = pd.Series(all_timestamps).sort_values()
            diffs = timestamps_series.diff().dropna()
            most_common_diff = diffs.mode()[0] if not diffs.empty else pd.Timedelta(days=1)

            freq_str = self._timedelta_to_freq(most_common_diff)

        elif self.step_frequency == "daily":
            freq_str = "D"
        elif self.step_frequency == "hourly":
            freq_str = "H"
        elif self.step_frequency == "minute":
            freq_str = "T"
        else:
            freq_str = self.step_frequency

        try:
            intervals = pd.date_range(
                start=self.start_date, end=self.end_date, freq=freq_str, tz="UTC"
            )
            return intervals
        except Exception as e:
            self.logger.error(f"Invalid frequency '{freq_str}': {e}")
            return pd.date_range(start=self.start_date, end=self.end_date, freq="D", tz="UTC")

    def run(self) -> BacktestResults:
        """Run backtest for all tickers.

        Returns:
            BacktestResults containing aggregated signals, trades, and metrics.
        """
        self._load_ohlcv_data()

        if not self.data_cache:
            self.logger.error("No OHLCV data loaded")
            return BacktestResults()

        step_intervals = self._determine_step_intervals()
        if len(step_intervals) == 0:
            self.logger.error("No time steps determined")
            return BacktestResults()

        self.logger.info(
            f"Running backtest with {len(step_intervals)} time steps "
            f"from {step_intervals[0]} to {step_intervals[-1]}"
        )

        all_signals = self._collect_signals_for_all_tickers(step_intervals)

        if not all_signals:
            self.logger.warning("No signals generated during backtest")
            return BacktestResults()

        combined_signals = pd.DataFrame(all_signals).sort_values("signal_time")
        return self._generate_results_for_all_tickers(combined_signals)

    def _collect_signals_for_all_tickers(self, step_intervals: pd.DatetimeIndex) -> list:
        """Collect signals for all tickers across time steps.

        Args:
            step_intervals: Time step intervals to process.

        Returns:
            List of signal dictionaries.
        """
        wrapper = BacktestStrategyWrapper(self.strategy, step_intervals[0], self.data_cache)
        original_query_ohlcv = self.strategy.query_ohlcv
        self.strategy.query_ohlcv = wrapper.query_ohlcv

        all_signals = []
        collected_signal_keys = set()
        last_collection_time: dict[str, pd.Timestamp] = {}

        try:
            for idx, current_time in enumerate(step_intervals):
                wrapper.current_time = current_time

                for ticker in self.tickers:
                    if ticker not in self.data_cache:
                        continue

                    try:
                        signals = self.strategy.run_strategy(ticker=ticker, write_signals=False)
                        new_signals, last_collection_time = (
                            self._process_signals_for_ticker_at_time(
                                signals=signals,
                                ticker=ticker,
                                current_time=current_time,
                                collected_signal_keys=collected_signal_keys,
                                last_collection_time=last_collection_time,
                            )
                        )
                        all_signals.extend(new_signals)

                    except Exception as e:
                        self.logger.error(
                            f"Error executing strategy for {ticker} at {current_time}: {e}"
                        )

                # Log progress every 10% of time steps
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

    def _generate_results_for_all_tickers(self, combined_signals: pd.DataFrame) -> BacktestResults:
        """Generate BacktestResults for all tickers.

        Args:
            combined_signals: DataFrame of all collected signals.

        Returns:
            BacktestResults with aggregated trades and metrics.
        """
        results = BacktestResults()
        results.signals = combined_signals
        results.strategy_name = self.strategy.strategy_name

        unique_tickers = combined_signals["ticker"].unique()
        all_trades = []

        for ticker in unique_tickers:
            ticker_signals = combined_signals[combined_signals["ticker"] == ticker]
            ohlcv_data = self.data_cache.get(ticker)

            journal = TradeJournal(
                signals=ticker_signals,
                strategy_name=self.strategy.strategy_name,
                ohlcv_data=ohlcv_data,
                capital_per_trade=self.capital_per_trade,
                risk_free_rate=self.risk_free_rate,
            )

            _metrics, trades = journal.generate_report()
            if not trades.empty:
                all_trades.append(trades)

        if all_trades:
            combined_trades = pd.concat(all_trades, ignore_index=True)
            executed_trades = self.execution_simulator.apply_execution(
                combined_trades, self.data_cache
            )

            group_journal = TradeJournal(
                signals=pd.DataFrame(),
                strategy_name=self.strategy.strategy_name,
                capital_per_trade=self.capital_per_trade,
                risk_free_rate=self.risk_free_rate,
            )
            results.metrics = group_journal.calculate_metrics(executed_trades)
            results.trades = executed_trades

        self.influx_client.close()
        return results
