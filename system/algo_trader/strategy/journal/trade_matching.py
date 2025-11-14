"""Trade matching for trading strategies.

This module provides functionality to match trading signals (buy/sell) into
executed trades, calculating PnL, efficiency, and other trade metrics.
"""

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.journal.efficiency import calculate_efficiency


def match_trades(
    signals: pd.DataFrame,
    strategy_name: str,
    capital_per_trade: float,
    ohlcv_data: pd.DataFrame | None = None,
    logger=None,
) -> pd.DataFrame:
    """Match trading signals into executed trades.

    Pairs entry signals (buy for LONG, sell for SHORT) with exit signals
    (sell for LONG, buy for SHORT) to create trade records, calculating
    PnL, efficiency, and other metrics.

    Args:
        signals: DataFrame containing trading signals with columns:
            ticker, signal_time, signal_type, price, side.
        strategy_name: Name of the strategy generating signals.
        capital_per_trade: Capital allocated per trade.
        ohlcv_data: Optional OHLCV DataFrame for efficiency calculation.
        logger: Optional logger instance. If not provided, creates a new logger.

    Returns:
        DataFrame containing matched trades with columns:
        entry_time, exit_time, entry_price, exit_price, gross_pnl,
        gross_pnl_pct, efficiency, etc.
    """
    logger = logger or get_logger("TradeMatching")
    if signals.empty:
        logger.warning("No signals to match")
        return pd.DataFrame()

    signals = signals.sort_values(["ticker", "signal_time"])
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

        is_entry = (side == "LONG" and signal_type == "buy") or (
            side == "SHORT" and signal_type == "sell"
        )
        is_exit = (side == "LONG" and signal_type == "sell") or (
            side == "SHORT" and signal_type == "buy"
        )

        if is_entry:
            open_positions[ticker].append(
                {"entry_time": timestamp, "entry_price": price, "side": side}
            )
        elif is_exit:
            if open_positions[ticker]:
                entry = open_positions[ticker].pop(0)
                shares = capital_per_trade / entry["entry_price"]

                if entry["side"] == "LONG":
                    gross_pnl = shares * (price - entry["entry_price"])
                else:
                    gross_pnl = shares * (entry["entry_price"] - price)

                gross_pnl_pct = (gross_pnl / capital_per_trade) * 100
                efficiency = calculate_efficiency(
                    ticker,
                    entry["entry_time"],
                    timestamp,
                    entry["entry_price"],
                    price,
                    ohlcv_data,
                    logger,
                )

                matched_trades.append(
                    {
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
                        "strategy": strategy_name,
                        "efficiency": efficiency,
                    }
                )

    total_unmatched = sum(len(positions) for positions in open_positions.values())
    if total_unmatched > 0:
        logger.debug(f"{total_unmatched} open positions remain unmatched")

    if not matched_trades:
        logger.warning("No trades could be matched")
        return pd.DataFrame()

    trades_df = pd.DataFrame(matched_trades)
    logger.debug(f"Matched {len(trades_df)} completed trades")
    return trades_df
