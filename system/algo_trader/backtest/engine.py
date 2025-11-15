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
    from system.algo_trader.strategy.base import BaseStrategy


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
        database: str = "ohlcv",
        execution_config: ExecutionConfig | None = None,
        capital_per_trade: float = 10000.0,
        risk_free_rate: float = 0.04,
        initial_account_value: float | None = None,
        trade_percentage: float | None = None,
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
        )

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

        return self.results_generator.generate_results_from_signals(
            combined_signals, ticker, ticker_data
        )

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
