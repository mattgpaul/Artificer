"""Results generator for backtest execution.

This module provides functionality to generate backtest results from trading signals,
including trade matching, execution simulation, and performance metrics calculation.
"""

from typing import TYPE_CHECKING

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.core.execution import ExecutionSimulator
from system.algo_trader.strategy.journal.journal import TradeJournal

if TYPE_CHECKING:
    from system.algo_trader.strategy.position_manager.position_manager import PositionManager


class BacktestResults:
    """Container for backtest execution results.

    Stores signals, executed trades, performance metrics, and strategy information
    from a backtest run.

    Attributes:
        signals: DataFrame containing all trading signals generated during backtest.
        trades: DataFrame containing executed trades with entry/exit details.
        metrics: Dictionary containing performance metrics (Sharpe ratio, drawdown, etc.).
        strategy_name: Name of the strategy used for the backtest.
    """

    def __init__(self) -> None:
        """Initialize empty BacktestResults container."""
        self.signals: pd.DataFrame = pd.DataFrame()
        self.trades: pd.DataFrame = pd.DataFrame()
        self.studies: pd.DataFrame = pd.DataFrame()
        self.metrics: dict = {}
        self.strategy_name: str = ""


class ResultsGenerator:
    """Generates backtest results from trading signals.

    This class orchestrates the process of converting trading signals into executed
    trades and calculating performance metrics using trade journal and execution simulation.

    Args:
        strategy: Strategy instance that generated the signals.
        execution_simulator: Simulator for applying execution costs and slippage.
        capital_per_trade: Capital allocated per trade.
        risk_free_rate: Risk-free rate for Sharpe ratio calculation.
        logger: Optional logger instance. If not provided, creates a new logger.
    """

    def __init__(
        self,
        strategy,
        execution_simulator: ExecutionSimulator,
        capital_per_trade: float,
        risk_free_rate: float,
        logger=None,
        initial_account_value: float | None = None,
        trade_percentage: float | None = None,
        position_manager: "PositionManager | None" = None,
    ):
        """Initialize ResultsGenerator with strategy and configuration.

        Args:
            strategy: Strategy instance that generated the signals.
            execution_simulator: Simulator for applying execution costs and slippage.
            capital_per_trade: Capital allocated per trade.
            risk_free_rate: Risk-free rate for Sharpe ratio calculation.
            logger: Optional logger instance. If not provided, creates a new logger.
            initial_account_value: Optional initial account value for account tracking.
            trade_percentage: Optional percentage of account to use per trade.
            position_manager: Optional PositionManager instance for filtering signals.
        """
        self.strategy = strategy
        self.execution_simulator = execution_simulator
        self.capital_per_trade = capital_per_trade
        self.risk_free_rate = risk_free_rate
        self.initial_account_value = initial_account_value
        self.trade_percentage = trade_percentage
        self.position_manager = position_manager
        self.logger = logger or get_logger(self.__class__.__name__)

    def generate_results_from_signals(
        self, signals: pd.DataFrame, ticker: str, ticker_data: pd.DataFrame
    ) -> BacktestResults:
        """Generate backtest results from signals for a single ticker.

        Processes trading signals to generate trades, apply execution simulation,
        and calculate performance metrics.

        Args:
            signals: DataFrame containing trading signals for the ticker.
            ticker: Ticker symbol being processed.
            ticker_data: OHLCV DataFrame for the ticker.

        Returns:
            BacktestResults object containing signals, trades, and metrics.
        """
        results = BacktestResults()
        results.strategy_name = self.strategy.strategy_name

        if self.position_manager is not None:
            ohlcv_by_ticker = {ticker: ticker_data}
            filtered_signals = self.position_manager.apply(signals, ohlcv_by_ticker)
            if filtered_signals.empty:
                self.logger.debug(f"{ticker}: Position manager filtered all signals")
                results.signals = signals
                return results
            results.signals = filtered_signals
            signals_to_use = filtered_signals
        else:
            results.signals = signals
            signals_to_use = signals

        mode = "raw" if self.position_manager is None else "pm_managed"
        pm_config = self.position_manager.config.to_dict() if self.position_manager else None

        journal = TradeJournal(
            signals=signals_to_use,
            strategy_name=self.strategy.strategy_name,
            ohlcv_data=ticker_data,
            capital_per_trade=self.capital_per_trade,
            risk_free_rate=self.risk_free_rate,
            initial_account_value=self.initial_account_value,
            trade_percentage=self.trade_percentage,
            mode=mode,
            pm_config=pm_config,
        )

        metrics, trades = journal.generate_report()
        results.metrics = metrics

        if not trades.empty:
            data_cache = {ticker: ticker_data}
            executed_trades = self.execution_simulator.apply_execution(trades, data_cache)
            results.trades = executed_trades

        return results

    def generate_results_for_all_tickers(
        self, combined_signals: pd.DataFrame, data_cache: dict[str, pd.DataFrame]
    ) -> BacktestResults:
        """Generate backtest results from signals for multiple tickers.

        Processes trading signals across multiple tickers, generates trades for each,
        applies execution simulation, and calculates aggregate performance metrics.

        Args:
            combined_signals: DataFrame containing trading signals for all tickers.
            data_cache: Dictionary mapping ticker symbols to OHLCV DataFrames.

        Returns:
            BacktestResults object containing combined signals, executed trades,
            and aggregate performance metrics.
        """
        results = BacktestResults()
        results.strategy_name = self.strategy.strategy_name

        if self.position_manager is not None:
            filtered_signals = self.position_manager.apply(combined_signals, data_cache)
            if filtered_signals.empty:
                self.logger.debug("Position manager filtered all signals")
                results.signals = combined_signals
                return results
            results.signals = filtered_signals
            signals_to_use = filtered_signals
        else:
            results.signals = combined_signals
            signals_to_use = combined_signals

        unique_tickers = signals_to_use["ticker"].unique()
        all_trades = []

        for ticker in unique_tickers:
            ticker_signals = signals_to_use[signals_to_use["ticker"] == ticker]
            ohlcv_data = data_cache.get(ticker)

            mode = "raw" if self.position_manager is None else "pm_managed"
            pm_config = self.position_manager.config.to_dict() if self.position_manager else None

            journal = TradeJournal(
                signals=ticker_signals,
                strategy_name=self.strategy.strategy_name,
                ohlcv_data=ohlcv_data,
                capital_per_trade=self.capital_per_trade,
                risk_free_rate=self.risk_free_rate,
                initial_account_value=self.initial_account_value,
                trade_percentage=self.trade_percentage,
                mode=mode,
                pm_config=pm_config,
            )

            _metrics, trades = journal.generate_report()
            if not trades.empty:
                all_trades.append(trades)

        if all_trades:
            combined_trades = pd.concat(all_trades, ignore_index=True)
            executed_trades = self.execution_simulator.apply_execution(combined_trades, data_cache)

            mode = "raw" if self.position_manager is None else "pm_managed"
            pm_config = self.position_manager.config.to_dict() if self.position_manager else None

            group_journal = TradeJournal(
                signals=pd.DataFrame(),
                strategy_name=self.strategy.strategy_name,
                capital_per_trade=self.capital_per_trade,
                risk_free_rate=self.risk_free_rate,
                initial_account_value=self.initial_account_value,
                trade_percentage=self.trade_percentage,
                mode=mode,
                pm_config=pm_config,
            )
            results.metrics = group_journal.calculate_metrics(executed_trades)
            results.trades = executed_trades

        return results
