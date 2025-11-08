"""Trading journal for tracking and analyzing trade performance.

This module provides the TradeJournal class for matching buy/sell signals into
completed trades and calculating performance metrics including P&L, max drawdown,
and Sharpe ratio.
"""

import numpy as np
import pandas as pd

from infrastructure.logging.logger import get_logger


class TradeJournal:
    """Trade journal for matching signals and calculating performance metrics.

    Uses FIFO (First In, First Out) matching to pair buy signals with sell signals,
    calculates position sizing based on fixed capital per trade, and computes
    comprehensive performance metrics.

    Attributes:
        signals: DataFrame with trading signals (buy/sell).
        capital_per_trade: Fixed capital allocated per trade.
        risk_free_rate: Annual risk-free rate for Sharpe ratio calculation.
        logger: Configured logger instance.
    """

    def __init__(
        self,
        signals: pd.DataFrame,
        capital_per_trade: float = 10000.0,
        risk_free_rate: float = 0.04,
    ):
        """Initialize trade journal with signals and configuration.

        Args:
            signals: DataFrame with columns: signal_type, price, signal_time, ticker.
            capital_per_trade: Fixed capital amount per trade (default: 10000).
            risk_free_rate: Annual risk-free rate for Sharpe calculation (default: 0.04).
        """
        self.signals = signals.copy()
        self.capital_per_trade = capital_per_trade
        self.risk_free_rate = risk_free_rate
        self.logger = get_logger(self.__class__.__name__)

        self.logger.info(
            f"TradeJournal initialized: capital={capital_per_trade}, "
            f"risk_free_rate={risk_free_rate:.2%}"
        )

    def match_trades(self) -> pd.DataFrame:
        """Match buy and sell signals into completed trades using FIFO.

        For each ticker, maintains a queue of unmatched buy signals and matches
        them with sell signals in chronological order.

        Returns:
            DataFrame with matched trades containing columns:
                - ticker: Stock symbol
                - entry_time: Buy signal timestamp
                - entry_price: Buy price
                - exit_time: Sell signal timestamp
                - exit_price: Sell price
                - shares: Number of shares (capital_per_trade / entry_price)
                - gross_pnl: Gross profit/loss in dollars
                - gross_pnl_pct: Gross profit/loss as percentage

        Example:
            >>> journal = TradeJournal(signals_df)
            >>> trades = journal.match_trades()
        """
        if self.signals.empty:
            self.logger.warning("No signals to match")
            return pd.DataFrame()

        # Sort by ticker and time to ensure chronological processing
        signals = self.signals.sort_values(["ticker", "signal_time"])

        matched_trades = []
        open_positions = {}  # ticker -> list of unmatched buys

        for _, signal in signals.iterrows():
            ticker = signal["ticker"]
            signal_type = signal["signal_type"]
            price = signal["price"]
            timestamp = signal["signal_time"]

            if ticker not in open_positions:
                open_positions[ticker] = []

            if signal_type == "buy":
                # Add to open positions queue
                open_positions[ticker].append(
                    {"entry_time": timestamp, "entry_price": price}
                )
            elif signal_type == "sell":
                # Match with oldest unmatched buy (FIFO)
                if open_positions[ticker]:
                    buy = open_positions[ticker].pop(0)
                    shares = self.capital_per_trade / buy["entry_price"]
                    gross_pnl = shares * (price - buy["entry_price"])
                    gross_pnl_pct = ((price - buy["entry_price"]) / buy["entry_price"]) * 100

                    matched_trades.append(
                        {
                            "ticker": ticker,
                            "entry_time": buy["entry_time"],
                            "entry_price": buy["entry_price"],
                            "exit_time": timestamp,
                            "exit_price": price,
                            "shares": shares,
                            "gross_pnl": gross_pnl,
                            "gross_pnl_pct": gross_pnl_pct,
                        }
                    )
                else:
                    self.logger.debug(
                        f"Unmatched sell signal for {ticker} at {timestamp} - no open position"
                    )

        # Log unmatched positions
        total_unmatched = sum(len(positions) for positions in open_positions.values())
        if total_unmatched > 0:
            self.logger.info(f"{total_unmatched} open positions remain unmatched")

        if not matched_trades:
            self.logger.warning("No trades could be matched")
            return pd.DataFrame()

        trades_df = pd.DataFrame(matched_trades)
        self.logger.info(f"Matched {len(trades_df)} completed trades")

        return trades_df

    def calculate_metrics(self, trades: pd.DataFrame) -> dict:
        """Calculate aggregate performance metrics from matched trades.

        Metrics computed:
            - total_trades: Number of completed trades
            - total_profit: Sum of all gross P&L
            - total_profit_pct: Total profit as percentage of capital deployed
            - max_drawdown: Maximum peak-to-trough decline in portfolio value
            - sharpe_ratio: Annualized Sharpe ratio (assumes daily returns)

        Args:
            trades: DataFrame with matched trades from match_trades().

        Returns:
            Dictionary with performance metrics.

        Example:
            >>> metrics = journal.calculate_metrics(trades_df)
            >>> print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        """
        if trades.empty:
            self.logger.warning("No trades to analyze")
            return {
                "total_trades": 0,
                "total_profit": 0.0,
                "total_profit_pct": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
            }

        total_trades = len(trades)
        total_profit = trades["gross_pnl"].sum()

        # Total capital deployed = number of trades * capital per trade
        total_capital = total_trades * self.capital_per_trade
        total_profit_pct = (total_profit / total_capital) * 100 if total_capital > 0 else 0.0

        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown(trades)

        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio(trades)

        metrics = {
            "total_trades": total_trades,
            "total_profit": total_profit,
            "total_profit_pct": total_profit_pct,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
        }

        self.logger.info(
            f"Metrics calculated: {total_trades} trades, "
            f"${total_profit:.2f} profit ({total_profit_pct:.2f}%), "
            f"{max_drawdown:.2f}% drawdown, {sharpe_ratio:.2f} Sharpe"
        )

        return metrics

    def _calculate_max_drawdown(self, trades: pd.DataFrame) -> float:
        """Calculate maximum drawdown from peak portfolio value.

        Tracks running portfolio value through all trades and identifies
        the maximum percentage decline from any peak.

        Args:
            trades: DataFrame with matched trades.

        Returns:
            Maximum drawdown as negative percentage.
        """
        if trades.empty:
            return 0.0

        # Sort trades by exit time to get chronological P&L
        trades_sorted = trades.sort_values("exit_time")

        # Calculate cumulative portfolio value
        cumulative_pnl = trades_sorted["gross_pnl"].cumsum()
        portfolio_value = self.capital_per_trade + cumulative_pnl

        # Track running maximum
        running_max = portfolio_value.expanding().max()

        # Calculate drawdown at each point
        drawdown = ((portfolio_value - running_max) / running_max) * 100

        # Max drawdown is the most negative value
        max_drawdown = drawdown.min()

        return max_drawdown if not pd.isna(max_drawdown) else 0.0

    def _calculate_sharpe_ratio(self, trades: pd.DataFrame) -> float:
        """Calculate annualized Sharpe ratio from trade returns.

        Assumes daily returns and annualizes using sqrt(252) trading days.

        Args:
            trades: DataFrame with matched trades.

        Returns:
            Annualized Sharpe ratio.
        """
        if trades.empty or len(trades) < 2:
            return 0.0

        # Calculate return per trade as percentage
        returns = trades["gross_pnl_pct"] / 100  # Convert percentage to decimal

        # Calculate daily risk-free rate
        daily_rf_rate = self.risk_free_rate / 252

        # Excess returns
        excess_returns = returns - daily_rf_rate

        # Mean and std of excess returns
        mean_excess = excess_returns.mean()
        std_excess = excess_returns.std()

        if std_excess == 0 or pd.isna(std_excess):
            return 0.0

        # Annualize Sharpe ratio (sqrt(252) for daily returns)
        sharpe = (mean_excess / std_excess) * np.sqrt(252)

        return sharpe if not pd.isna(sharpe) else 0.0

    def generate_report(self) -> tuple[dict, pd.DataFrame]:
        """Generate complete trading journal report.

        Main entry point that combines trade matching and metrics calculation.

        Returns:
            Tuple of (metrics_dict, trades_df):
                - metrics_dict: Performance metrics from calculate_metrics()
                - trades_df: Matched trades from match_trades()

        Example:
            >>> journal = TradeJournal(signals_df)
            >>> metrics, trades = journal.generate_report()
        """
        self.logger.info("Generating trading journal report")

        trades = self.match_trades()
        metrics = self.calculate_metrics(trades)

        return metrics, trades
