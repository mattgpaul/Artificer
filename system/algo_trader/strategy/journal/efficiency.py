"""Trade efficiency calculator for trading strategies.

This module provides functionality to calculate trade efficiency, measuring
how well a trade captured the maximum potential profit available during the holding period.
"""

import pandas as pd

from infrastructure.logging.logger import get_logger


def calculate_efficiency(
    ticker: str,
    entry_time: pd.Timestamp,
    exit_time: pd.Timestamp,
    entry_price: float,
    exit_price: float,
    ohlcv_data: pd.DataFrame | None = None,
    logger=None,
) -> float:
    """Calculate trade efficiency percentage.

    Measures how well a trade captured the maximum potential profit available
    during the holding period, expressed as a percentage (0-100%).

    Args:
        ticker: Ticker symbol for the trade.
        entry_time: Timestamp when trade was entered.
        exit_time: Timestamp when trade was exited.
        entry_price: Price at which trade was entered.
        exit_price: Price at which trade was exited.
        ohlcv_data: Optional OHLCV DataFrame for calculating maximum price.
        logger: Optional logger instance. If not provided, creates a new logger.

    Returns:
        Efficiency percentage (0-100%), or 0.0 if calculation fails.
    """
    logger = logger or get_logger("EfficiencyCalculator")
    if ohlcv_data is None or ohlcv_data.empty:
        return 0.0

    try:
        if entry_time.tz is None:
            entry_time = entry_time.tz_localize("UTC")
        else:
            entry_time = entry_time.tz_convert("UTC")

        if exit_time.tz is None:
            exit_time = exit_time.tz_localize("UTC")
        else:
            exit_time = exit_time.tz_convert("UTC")

        ohlcv_utc = ohlcv_data.copy()
        if ohlcv_utc.index.tz is None:
            ohlcv_utc.index = ohlcv_utc.index.tz_localize("UTC")
        else:
            ohlcv_utc.index = ohlcv_utc.index.tz_convert("UTC")

        trade_data = ohlcv_utc[(ohlcv_utc.index >= entry_time) & (ohlcv_utc.index <= exit_time)]

        if trade_data.empty:
            return 0.0

        actual_pnl = exit_price - entry_price

        max_price = trade_data["high"].max()
        potential_pnl = max_price - entry_price

        if potential_pnl <= 0:
            return 0.0

        efficiency = (actual_pnl / potential_pnl) * 100
        return max(0.0, min(100.0, efficiency))

    except Exception as e:
        logger.debug(f"Failed to calculate efficiency for {ticker}: {e}")
        return 0.0
