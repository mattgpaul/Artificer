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
                df["time"] = pd.to_datetime(df["time"])
                df = df.set_index("time")

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

        wrapper = BacktestStrategyWrapper(self.strategy, step_intervals[0], self.data_cache)
        self.strategy.query_ohlcv = wrapper.query_ohlcv

        all_signals = []
        collected_signal_keys = set()

        for current_time in step_intervals:
            wrapper.current_time = current_time

            for ticker in self.tickers:
                if ticker not in self.data_cache:
                    continue

                try:
                    signals = self.strategy.run_strategy(ticker=ticker, write_signals=False)

                    if not signals.empty:
                        signals["signal_time"] = pd.to_datetime(signals["signal_time"], utc=True)
                        current_time_normalized = pd.Timestamp(current_time).tz_localize("UTC") if current_time.tz is None else current_time.tz_convert("UTC")
                        current_time_end = current_time_normalized + pd.Timedelta(days=1)
                        
                        current_time_ns = current_time_normalized.value
                        current_time_end_ns = current_time_end.value
                        signal_times_ns = pd.to_datetime(signals["signal_time"], utc=True).astype("int64")
                        
                        mask = (signal_times_ns >= current_time_ns) & (signal_times_ns < current_time_end_ns)
                        current_step_signals = signals[mask]

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
                                signal.get("price", 0),
                            )
                            if signal_key not in collected_signal_keys:
                                collected_signal_keys.add(signal_key)
                                all_signals.append(signal.to_dict())

                except Exception as e:
                    self.logger.error(f"Error executing strategy for {ticker} at {current_time}: {e}")

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

