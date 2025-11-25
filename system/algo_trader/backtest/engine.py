"""Backtesting engine for trading strategies.

This module provides the core backtesting functionality, including:
- BacktestEngine: Main engine for running backtests
- BacktestResults: Container for backtest results
"""

from typing import TYPE_CHECKING

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.core.data_loader import DataLoader
from system.algo_trader.backtest.core.execution import ExecutionConfig, ExecutionSimulator
from system.algo_trader.backtest.core.results_generator import BacktestResults, ResultsGenerator
from system.algo_trader.backtest.core.signal_collector import SignalCollector
from system.algo_trader.backtest.core.time_stepper import TimeStepper
from system.algo_trader.influx.market_data_influx import MarketDataInflux

if TYPE_CHECKING:
    from system.algo_trader.strategy.filters.core import FilterPipeline
    from system.algo_trader.strategy.position_manager.position_manager import PositionManager
    from system.algo_trader.strategy.strategy import Strategy


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
        strategy: "Strategy",
        tickers: list[str],
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        step_frequency: str,
        database: str = "ohlcv",
        execution_config: ExecutionConfig | None = None,
        capital_per_trade: float = 10000.0,
        risk_free_rate: float = 0.04,
        initial_account_value: float | None = None,
        trade_percentage: float | None = None,
        filter_pipeline: "FilterPipeline | None" = None,
        position_manager: "PositionManager | None" = None,
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
            initial_account_value: Optional initial account value for account tracking.
            trade_percentage: Optional percentage of account to use per trade.
            filter_pipeline: Optional FilterPipeline instance for filtering signals.
            position_manager: Optional PositionManager instance for filtering signals.
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

        self.data_loader = DataLoader(self.influx_client, self.logger)
        self.time_stepper = TimeStepper(
            self.step_frequency, self.start_date, self.end_date, self.logger
        )
        self.signal_collector = SignalCollector(self.strategy, self.logger)
        self.results_generator = ResultsGenerator(
            self.strategy,
            self.execution_simulator,
            self.capital_per_trade,
            self.risk_free_rate,
            self.logger,
            initial_account_value,
            trade_percentage,
            filter_pipeline,
            position_manager,
        )

    def _collect_studies_for_ticker(
        self,
        ticker: str,
        ticker_data: pd.DataFrame,
        step_intervals: pd.DatetimeIndex,
        signals: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        study_specs = self.strategy.get_study_specs()
        if not study_specs:
            return pd.DataFrame()

        processed_bars: dict[pd.Timestamp, dict] = {}

        buy_flags: dict[pd.Timestamp, bool] = {}
        sell_flags: dict[pd.Timestamp, bool] = {}
        if signals is not None and not signals.empty:
            try:
                signals_df = signals.copy()
                signals_df["signal_time"] = pd.to_datetime(signals_df["signal_time"], utc=True)
                if "signal_type" in signals_df.columns:
                    for ts, group in signals_df.groupby("signal_time"):
                        buy_flags[ts] = bool((group["signal_type"] == "buy").any())
                        sell_flags[ts] = bool((group["signal_type"] == "sell").any())
            except Exception as e:
                self.logger.debug(f"{ticker}: Error computing signal flags for studies: {e}")

        for current_time in step_intervals:
            window = self.signal_collector._slice_window(ticker_data, current_time)
            if window.empty:
                continue

            bar_timestamp = window.index[-1]
            if bar_timestamp in processed_bars:
                continue

            row_data: dict = {}

            for spec in study_specs:
                min_bars = spec.min_bars or spec.params.get("window", 0)
                if len(window) < min_bars:
                    field_name = spec.study.get_field_name(**spec.params)
                    row_data[field_name] = None
                    continue

                try:
                    study_result = spec.study.compute(
                        ohlcv_data=window,
                        ticker=ticker,
                        **spec.params,
                    )
                    field_name = spec.study.get_field_name(**spec.params)
                    if study_result is not None and len(study_result) > 0:
                        row_data[field_name] = float(study_result.iloc[-1])
                    else:
                        row_data[field_name] = None
                except Exception as e:
                    field_name = spec.study.get_field_name(**spec.params)
                    self.logger.debug(
                        f"{ticker}: Error computing {field_name} at {bar_timestamp}: {e}"
                    )
                    row_data[field_name] = None

            # Boolean buy/sell signal flags based on raw strategy signals
            row_data["buy_signal"] = bool(buy_flags.get(bar_timestamp, False))
            row_data["sell_signal"] = bool(sell_flags.get(bar_timestamp, False))

            processed_bars[bar_timestamp] = row_data

        if not processed_bars:
            return pd.DataFrame()

        studies_df = pd.DataFrame.from_dict(processed_bars, orient="index")
        studies_df.index.name = "datetime"
        return studies_df

    def run_ticker(self, ticker: str) -> BacktestResults:
        """Run backtest for a single ticker.

        Args:
            ticker: Ticker symbol to backtest.

        Returns:
            BacktestResults containing signals, trades, and metrics.
        """
        ticker_data = self.data_loader.load_ticker_ohlcv_data(
            ticker, self.start_date, self.end_date
        )
        if ticker_data is None or ticker_data.empty:
            self.logger.warning(
                f"{ticker}: No OHLCV data found in date range "
                f"{self.start_date.date()} to {self.end_date.date()}"
            )
            return BacktestResults()

        self.logger.debug(f"{ticker}: Loaded {len(ticker_data)} OHLCV records")

        data_cache = {ticker: ticker_data}
        step_intervals = self.time_stepper.determine_step_intervals(data_cache)
        if len(step_intervals) == 0:
            self.logger.warning(f"No time steps determined for {ticker}")
            return BacktestResults()

        all_signals = self.signal_collector.collect_signals_for_ticker(
            ticker, step_intervals, data_cache
        )

        if not all_signals:
            self.logger.debug(
                f"{ticker}: No signals generated "
                "(insufficient data for SMA crossover or no crossovers detected)"
            )
            return BacktestResults()

        combined_signals = pd.DataFrame(all_signals).sort_values("signal_time")
        self.logger.debug(f"{ticker}: Generated {len(combined_signals)} unique signals")

        results = self.results_generator.generate_results_from_signals(
            combined_signals, ticker, ticker_data
        )

        studies_df = self._collect_studies_for_ticker(
            ticker,
            ticker_data,
            step_intervals,
            combined_signals,
        )
        results.studies = studies_df

        return results

    def run(self) -> BacktestResults:
        """Run backtest for all tickers.

        Returns:
            BacktestResults containing aggregated signals, trades, and metrics.
        """
        self.data_cache = self.data_loader.load_ohlcv_data(
            self.tickers, self.start_date, self.end_date
        )

        if not self.data_cache:
            self.logger.error("No OHLCV data loaded")
            return BacktestResults()

        step_intervals = self.time_stepper.determine_step_intervals(self.data_cache)
        if len(step_intervals) == 0:
            self.logger.error("No time steps determined")
            return BacktestResults()

        self.logger.info(
            f"Running backtest with {len(step_intervals)} time steps "
            f"from {step_intervals[0]} to {step_intervals[-1]}"
        )

        all_signals = self.signal_collector.collect_signals_for_all_tickers(
            step_intervals, self.tickers, self.data_cache
        )

        if not all_signals:
            self.logger.warning("No signals generated during backtest")
            return BacktestResults()

        combined_signals = pd.DataFrame(all_signals).sort_values("signal_time")
        results = self.results_generator.generate_results_for_all_tickers(
            combined_signals, self.data_cache
        )

        self.influx_client.close()
        return results
