"""Trading journal for strategy performance analysis.

This module provides functionality to match trading signals into trades,
calculate performance metrics, and generate comprehensive trading reports.
"""

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.domain.strategy.journal.calculator import calculate_metrics
from system.algo_trader.domain.strategy.journal.trade_matching import match_trades


class TradeJournal:
    """Generates trading journal reports from signals.

    Matches trading signals into executed trades, calculates performance metrics,
    and generates comprehensive reports for strategy evaluation.

    Args:
        signals: DataFrame containing trading signals.
        strategy_name: Name of the strategy generating signals.
        ohlcv_data: Optional OHLCV DataFrame for trade matching and efficiency calculation.
        capital_per_trade: Capital allocated per trade. Defaults to 10000.0.
        risk_free_rate: Annual risk-free rate for Sharpe ratio. Defaults to 0.04.
    """

    def __init__(
        self,
        signals: pd.DataFrame,
        strategy_name: str,
        ohlcv_data: pd.DataFrame = None,
        capital_per_trade: float = 10000.0,
        risk_free_rate: float = 0.04,
        initial_account_value: float | None = None,
        trade_percentage: float | None = None,
        mode: str = "pm_managed",
        pm_config: dict | None = None,
    ):
        """Initialize TradeJournal with signals and configuration.

        Args:
            signals: DataFrame containing trading signals.
            strategy_name: Name of the strategy generating signals.
            ohlcv_data: Optional OHLCV DataFrame for trade matching and efficiency calculation.
            capital_per_trade: Capital allocated per trade. Defaults to 10000.0.
            risk_free_rate: Annual risk-free rate for Sharpe ratio. Defaults to 0.04.
            initial_account_value: Optional initial account value for account tracking.
            trade_percentage: Optional percentage of account to use per trade.
            mode: Position management mode. Defaults to "pm_managed".
            pm_config: Optional position manager configuration dictionary.
        """
        self.signals = signals.copy()
        self.strategy_name = strategy_name
        self.ohlcv_data = ohlcv_data
        self.capital_per_trade = capital_per_trade
        self.risk_free_rate = risk_free_rate
        self.initial_account_value = initial_account_value
        self.trade_percentage = trade_percentage
        self.mode = mode
        self.pm_config = pm_config
        self.logger = get_logger(self.__class__.__name__)

        self.logger.debug(
            f"TradeJournal initialized: strategy={strategy_name}, "
            f"capital={capital_per_trade}, risk_free_rate={risk_free_rate:.2%}"
        )

    def match_trades(self) -> pd.DataFrame:
        """Match trading signals into executed trades.

        Pairs entry and exit signals to create trade records with PnL calculations.

        Returns:
            DataFrame containing matched trades with entry/exit details and PnL.
        """
        return match_trades(
            self.signals,
            self.strategy_name,
            self.capital_per_trade,
            self.ohlcv_data,
            self.logger,
            self.initial_account_value,
            self.trade_percentage,
            self.mode,
            self.pm_config,
        )

    def calculate_metrics(self, trades: pd.DataFrame) -> dict:
        """Calculate performance metrics from trades.

        Args:
            trades: DataFrame containing executed trades.

        Returns:
            Dictionary containing performance metrics.
        """
        return calculate_metrics(trades, self.capital_per_trade, self.risk_free_rate, self.logger)

    def generate_report(self) -> tuple[dict, pd.DataFrame]:
        """Generate comprehensive trading journal report.

        Matches signals into trades and calculates all performance metrics.

        Returns:
            Tuple of (metrics_dict, trades_dataframe) containing complete report.
        """
        self.logger.debug("Generating trading journal report")

        trades = self.match_trades()
        metrics = self.calculate_metrics(trades)

        return metrics, trades
