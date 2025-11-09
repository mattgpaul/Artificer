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
        strategy_name: str,
        ohlcv_data: pd.DataFrame = None,
        capital_per_trade: float = 10000.0,
        risk_free_rate: float = 0.04,
    ):
        """Initialize trade journal with signals and configuration.

        Args:
            signals: DataFrame with columns: signal_type, price, signal_time, ticker, side.
            strategy_name: Name of the strategy that generated signals.
            ohlcv_data: Optional OHLCV data for efficiency calculation.
            capital_per_trade: Fixed capital amount per trade (default: 10000).
            risk_free_rate: Annual risk-free rate for Sharpe calculation (default: 0.04).
        """
        self.signals = signals.copy()
        self.strategy_name = strategy_name
        self.ohlcv_data = ohlcv_data
        self.capital_per_trade = capital_per_trade
        self.risk_free_rate = risk_free_rate
        self.logger = get_logger(self.__class__.__name__)

        self.logger.info(
            f"TradeJournal initialized: strategy={strategy_name}, "
            f"capital={capital_per_trade}, risk_free_rate={risk_free_rate:.2%}"
        )

    def match_trades(self) -> pd.DataFrame:
        """Match buy and sell signals into completed trades using FIFO.

        For LONG strategies: Match buy entry with sell exit
        For SHORT strategies: Match sell entry with buy exit

        Returns:
            DataFrame with matched trades containing columns:
                - ticker, entry_time, entry_price, exit_time, exit_price
                - shares, gross_pnl, gross_pnl_pct, side, status, strategy, efficiency
        """
        if self.signals.empty:
            self.logger.warning("No signals to match")
            return pd.DataFrame()

        signals = self.signals.sort_values(["ticker", "signal_time"])
        matched_trades = []
        open_positions = {}

        for _, signal in signals.iterrows():
            ticker = signal["ticker"]
            signal_type = signal["signal_type"]
            price = signal["price"]
            timestamp = signal["signal_time"]
            side = signal.get("side", "LONG")

            if ticker not in open_positions:
                open_positions[ticker] = []

            # LONG: buy entry, sell exit | SHORT: sell entry, buy exit
            is_entry = (side == "LONG" and signal_type == "buy") or (side == "SHORT" and signal_type == "sell")
            is_exit = (side == "LONG" and signal_type == "sell") or (side == "SHORT" and signal_type == "buy")

            if is_entry:
                open_positions[ticker].append(
                    {"entry_time": timestamp, "entry_price": price, "side": side}
                )
            elif is_exit:
                if open_positions[ticker]:
                    entry = open_positions[ticker].pop(0)
                    shares = self.capital_per_trade / entry["entry_price"]

                    # Calculate P&L based on side
                    if entry["side"] == "LONG":
                        gross_pnl = shares * (price - entry["entry_price"])
                    else:  # SHORT
                        gross_pnl = shares * (entry["entry_price"] - price)

                    gross_pnl_pct = (gross_pnl / self.capital_per_trade) * 100
                    efficiency = self._calculate_efficiency(ticker, entry["entry_time"], timestamp, entry["entry_price"], price)

                    matched_trades.append({
                        "ticker": ticker,
                        "entry_time": entry["entry_time"],
                        "entry_price": entry["entry_price"],
                        "exit_time": timestamp,
                        "exit_price": price,
                        "shares": shares,
                        "gross_pnl": gross_pnl,
                        "gross_pnl_pct": gross_pnl_pct,
                        "side": entry["side"],
                        "status": "CLOSED",
                        "strategy": self.strategy_name,
                        "efficiency": efficiency,
                    })

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

        Returns:
            Dictionary with performance metrics including total_trades, total_profit,
            total_profit_pct, max_drawdown, sharpe_ratio, avg_efficiency.
        """
        if trades.empty:
            self.logger.warning("No trades to analyze")
            return {
                "total_trades": 0,
                "total_profit": 0.0,
                "total_profit_pct": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "avg_efficiency": 0.0,
            }

        total_trades = len(trades)
        total_profit = trades["gross_pnl"].sum()
        total_capital = total_trades * self.capital_per_trade
        total_profit_pct = (total_profit / total_capital) * 100 if total_capital > 0 else 0.0

        max_drawdown = self._calculate_max_drawdown(trades)
        sharpe_ratio = self._calculate_sharpe_ratio(trades)
        avg_efficiency = trades["efficiency"].mean() if "efficiency" in trades.columns else 0.0

        metrics = {
            "total_trades": total_trades,
            "total_profit": total_profit,
            "total_profit_pct": total_profit_pct,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "avg_efficiency": avg_efficiency,
        }

        self.logger.info(
            f"Metrics calculated: {total_trades} trades, "
            f"${total_profit:.2f} profit ({total_profit_pct:.2f}%), "
            f"{max_drawdown:.2f}% drawdown, {sharpe_ratio:.2f} Sharpe, "
            f"{avg_efficiency:.1f}% efficiency"
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

    def _calculate_efficiency(
        self,
        ticker: str,
        entry_time: pd.Timestamp,
        exit_time: pd.Timestamp,
        entry_price: float,
        exit_price: float,
    ) -> float:
        """Calculate trade efficiency as actual P&L vs potential P&L.

        Efficiency = (actual_pnl / potential_pnl) * 100
        where potential_pnl is the maximum favorable movement during the trade.

        Returns:
            Efficiency percentage. Returns 0 if OHLCV data unavailable.
        """
        if self.ohlcv_data is None or self.ohlcv_data.empty:
            return 0.0

        try:
            # Filter OHLCV data for the trade period
            trade_data = self.ohlcv_data[
                (self.ohlcv_data.index >= entry_time) & (self.ohlcv_data.index <= exit_time)
            ]

            if trade_data.empty:
                return 0.0

            # Calculate actual P&L
            actual_pnl = exit_price - entry_price

            # Calculate potential P&L (best case scenario during trade)
            max_price = trade_data["high"].max()
            potential_pnl = max_price - entry_price

            if potential_pnl <= 0:
                return 0.0

            efficiency = (actual_pnl / potential_pnl) * 100
            return max(0.0, min(100.0, efficiency))  # Clamp to 0-100%

        except Exception as e:
            self.logger.debug(f"Failed to calculate efficiency for {ticker}: {e}")
            return 0.0

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
