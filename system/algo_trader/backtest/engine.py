from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.execution import ExecutionConfig, ExecutionSimulator
from system.algo_trader.backtest.strategy_wrapper import BacktestStrategyWrapper
from system.algo_trader.influx.market_data_influx import MarketDataInflux
from system.algo_trader.strategy.journal import TradeJournal

if TYPE_CHECKING:
    from system.algo_trader.strategy.base import BaseStrategy


class BacktestResults:
    def __init__(self):
        self.signals: pd.DataFrame = pd.DataFrame()
        self.trades: pd.DataFrame = pd.DataFrame()
        self.metrics: dict = {}
        self.strategy_name: str = ""


class BacktestEngine:
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
    ):
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
            self.logger.info(f"Loaded {len(df)} records for {ticker}")

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
            intervals = pd.date_range(start=self.start_date, end=self.end_date, freq=freq_str, tz="UTC")
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

    def run(self) -> BacktestResults:
        self._load_ohlcv_data()

        if not self.data_cache:
            self.logger.error("No OHLCV data loaded")
            return BacktestResults()

        step_intervals = self._determine_step_intervals()
        if len(step_intervals) == 0:
            self.logger.error("No time steps determined")
            return BacktestResults()

        self.logger.info(f"Running backtest with {len(step_intervals)} time steps from {step_intervals[0]} to {step_intervals[-1]}")

        wrapper = BacktestStrategyWrapper(self.strategy, step_intervals[0], self.data_cache)
        self.strategy.query_ohlcv = wrapper.query_ohlcv

        all_signals = []
        collected_signal_keys = set()
        # Track last collection time per ticker to only collect new signals
        last_collection_time: dict[str, pd.Timestamp] = {}

        for idx, current_time in enumerate(step_intervals):
            wrapper.current_time = current_time
            
            # Normalize current_time to UTC
            current_time_normalized = pd.Timestamp(current_time).tz_localize("UTC") if current_time.tz is None else current_time.tz_convert("UTC")

            for ticker in self.tickers:
                if ticker not in self.data_cache:
                    continue

                try:
                    signals = self.strategy.run_strategy(ticker=ticker, write_signals=False)

                    if not signals.empty:
                        # Ensure signal_time is timezone-aware (UTC)
                        signals["signal_time"] = pd.to_datetime(signals["signal_time"], utc=True)
                        if signals["signal_time"].dt.tz is None:
                            signals["signal_time"] = signals["signal_time"].dt.tz_localize("UTC")
                        else:
                            signals["signal_time"] = signals["signal_time"].dt.tz_convert("UTC")
                        
                        # Filter signals: only collect signals that occurred at or before current_time
                        # and are new (haven't been collected in a previous time step)
                        mask = signals["signal_time"] <= current_time_normalized
                        
                        # If we've collected signals for this ticker before, only get new ones
                        if ticker in last_collection_time:
                            mask = mask & (signals["signal_time"] > last_collection_time[ticker])
                        
                        current_step_signals = signals[mask]

                        # Collect all new unique signals
                        for _, signal in current_step_signals.iterrows():
                            signal_time_val = signal["signal_time"]
                            if isinstance(signal_time_val, pd.Timestamp):
                                signal_time_normalized = signal_time_val.tz_localize("UTC") if signal_time_val.tz is None else signal_time_val.tz_convert("UTC")
                            else:
                                signal_time_normalized = pd.Timestamp(signal_time_val, tz="UTC")
                            
                            signal_key = (
                                ticker,
                                signal_time_normalized,
                                signal["signal_type"],
                                float(signal.get("price", 0)),  # Ensure price is float for consistent comparison
                            )
                            if signal_key not in collected_signal_keys:
                                collected_signal_keys.add(signal_key)
                                all_signals.append(signal.to_dict())
                        
                        # Update last collection time for this ticker to the max signal time collected
                        if not current_step_signals.empty:
                            max_signal_time = current_step_signals["signal_time"].max()
                            if ticker not in last_collection_time or max_signal_time > last_collection_time[ticker]:
                                last_collection_time[ticker] = max_signal_time
                        elif ticker not in last_collection_time:
                            # First time collecting for this ticker (even if no signals), set to current_time
                            last_collection_time[ticker] = current_time_normalized

                except Exception as e:
                    self.logger.error(f"Error executing strategy for {ticker} at {current_time}: {e}")
            
            # Log progress every 10% of time steps
            if (idx + 1) % max(1, len(step_intervals) // 10) == 0 or idx == len(step_intervals) - 1:
                progress_pct = ((idx + 1) / len(step_intervals)) * 100
                self.logger.info(f"Backtest progress: {progress_pct:.0f}% ({idx + 1}/{len(step_intervals)} steps, {len(all_signals)} signals collected)")

        if not all_signals:
            self.logger.warning("No signals generated during backtest")
            return BacktestResults()

        combined_signals = pd.DataFrame(all_signals).sort_values("signal_time")

        results = BacktestResults()
        results.signals = combined_signals
        results.strategy_name = self.strategy.strategy_name

        unique_tickers = combined_signals["ticker"].unique()
        all_trades = []

        for ticker in unique_tickers:
            ticker_signals = combined_signals[combined_signals["ticker"] == ticker]

            ohlcv_data = None
            if ticker in self.data_cache:
                ohlcv_data = self.data_cache[ticker]

            journal = TradeJournal(
                signals=ticker_signals,
                strategy_name=self.strategy.strategy_name,
                ohlcv_data=ohlcv_data,
                capital_per_trade=self.capital_per_trade,
                risk_free_rate=self.risk_free_rate,
            )

            metrics, trades = journal.generate_report()

            if not trades.empty:
                all_trades.append(trades)

        if all_trades:
            combined_trades = pd.concat(all_trades, ignore_index=True)
            executed_trades = self.execution_simulator.apply_execution(combined_trades, self.data_cache)

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

