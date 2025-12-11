"""Performance metrics calculator for trading strategies.

This module provides functionality to calculate performance metrics from
executed trades, including Sharpe ratio, drawdown, win rate, and efficiency.
"""

import numpy as np
import pandas as pd

from infrastructure.logging.logger import get_logger


def calculate_metrics(
    trades: pd.DataFrame, capital_per_trade: float, risk_free_rate: float, logger=None
) -> dict:
    """Calculate comprehensive performance metrics from trades.

    Computes various performance metrics including total profit, drawdown,
    Sharpe ratio, win rate, and efficiency from executed trades.

    Args:
        trades: DataFrame containing executed trades with required columns.
        capital_per_trade: Capital allocated per trade.
        risk_free_rate: Annual risk-free rate for Sharpe ratio calculation.
        logger: Optional logger instance. If not provided, creates a new logger.

    Returns:
        Dictionary containing performance metrics:
        - total_trades: Number of trades executed
        - total_profit: Total profit in dollars
        - total_profit_pct: Total profit as percentage
        - max_drawdown: Maximum drawdown percentage
        - sharpe_ratio: Annualized Sharpe ratio
        - avg_efficiency: Average trade efficiency percentage
        - avg_return_pct: Average return per trade percentage
        - avg_time_held: Average time held in hours
        - win_rate: Percentage of winning trades
    """
    logger = logger or get_logger("MetricsCalculator")
    if trades.empty:
        logger.warning("No trades to analyze")
        return {
            "total_trades": 0,
            "total_profit": 0.0,
            "total_profit_pct": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "avg_efficiency": 0.0,
            "avg_return_pct": 0.0,
            "avg_time_held": 0.0,
            "win_rate": 0.0,
        }

    total_trades = len(trades)
    total_profit = trades["gross_pnl"].sum()
    total_capital = total_trades * capital_per_trade
    total_profit_pct = (total_profit / total_capital) * 100 if total_capital > 0 else 0.0

    max_drawdown = calculate_max_drawdown(trades, capital_per_trade)
    sharpe_ratio = calculate_sharpe_ratio(trades, risk_free_rate)
    avg_efficiency = trades["efficiency"].mean() if "efficiency" in trades.columns else 0.0

    avg_return_pct = trades["gross_pnl_pct"].mean()
    winning_trades = (trades["gross_pnl"] > 0).sum()
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0

    time_deltas = trades["exit_time"] - trades["entry_time"]
    avg_time_held = time_deltas.mean().total_seconds() / 3600

    metrics = {
        "total_trades": total_trades,
        "total_profit": total_profit,
        "total_profit_pct": total_profit_pct,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "avg_efficiency": avg_efficiency,
        "avg_return_pct": avg_return_pct,
        "avg_time_held": avg_time_held,
        "win_rate": win_rate,
    }

    logger.debug(
        f"Metrics calculated: {total_trades} trades, "
        f"${total_profit:.2f} profit ({total_profit_pct:.2f}%), "
        f"{max_drawdown:.2f}% drawdown, {sharpe_ratio:.2f} Sharpe, "
        f"{avg_efficiency:.1f}% efficiency, {win_rate:.1f}% win rate"
    )

    return metrics


def calculate_max_drawdown(trades: pd.DataFrame, capital_per_trade: float) -> float:
    """Calculate maximum drawdown from trades.

    Computes the maximum peak-to-trough decline in portfolio value.

    Args:
        trades: DataFrame containing executed trades sorted by exit_time.
        capital_per_trade: Capital allocated per trade.

    Returns:
        Maximum drawdown as a percentage (negative value).
    """
    if trades.empty:
        return 0.0

    trades_sorted = trades.sort_values("exit_time")

    cumulative_pnl = trades_sorted["gross_pnl"].cumsum()
    portfolio_value = capital_per_trade + cumulative_pnl

    running_max = portfolio_value.expanding().max()

    drawdown = ((portfolio_value - running_max) / running_max) * 100

    max_drawdown = drawdown.min()

    return max_drawdown if not pd.isna(max_drawdown) else 0.0


def calculate_sharpe_ratio(trades: pd.DataFrame, risk_free_rate: float) -> float:
    """Calculate annualized Sharpe ratio from trades.

    Computes Sharpe ratio using excess returns over risk-free rate,
    annualized to 252 trading days.

    Args:
        trades: DataFrame containing executed trades with gross_pnl_pct column.
        risk_free_rate: Annual risk-free rate.

    Returns:
        Annualized Sharpe ratio, or 0.0 if insufficient data or zero volatility.
    """
    if trades.empty or len(trades) < 2:
        return 0.0

    returns = trades["gross_pnl_pct"] / 100

    daily_rf_rate = risk_free_rate / 252

    excess_returns = returns - daily_rf_rate

    mean_excess = excess_returns.mean()
    std_excess = excess_returns.std()

    if std_excess == 0 or pd.isna(std_excess):
        return 0.0

    sharpe = (mean_excess / std_excess) * np.sqrt(252)

    return sharpe if not pd.isna(sharpe) else 0.0
