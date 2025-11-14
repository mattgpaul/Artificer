"""Sequential execution for trading strategies.

This module provides functionality to execute trading strategies sequentially
across multiple tickers, useful for debugging or when threading is not desired.
"""

import pandas as pd

from infrastructure.logging.logger import get_logger


def run_sequential(
    strategy,
    tickers: list[str],
    start_time: str | None,
    end_time: str | None,
    limit: int | None,
    write_signals: bool,
    logger=None,
) -> pd.DataFrame:
    """Execute strategy sequentially for multiple tickers.

    Runs strategy for each ticker one at a time in the current thread,
    collecting and combining signal summaries.

    Args:
        strategy: Strategy instance to execute.
        tickers: List of ticker symbols to process.
        start_time: Optional start time for data query.
        end_time: Optional end time for data query.
        limit: Optional limit on number of data points.
        write_signals: Whether to write signals to InfluxDB.
        logger: Optional logger instance. If not provided, creates a new logger.

    Returns:
        Combined DataFrame containing signals from all tickers.
    """
    logger = logger or get_logger("SequentialStrategy")
    all_summaries = []

    for ticker in tickers:
        summary = strategy.run_strategy(ticker, start_time, end_time, limit, write_signals)
        if not summary.empty:
            all_summaries.append(summary)

    if not all_summaries:
        logger.info("No signals generated for any tickers")
        return pd.DataFrame()

    combined = pd.concat(all_summaries, ignore_index=True)
    log_multi_summary(combined, logger)
    return combined


def log_multi_summary(combined: pd.DataFrame, logger=None) -> None:
    """Log summary statistics for multi-ticker strategy execution.

    Args:
        combined: DataFrame containing signals from all tickers.
        logger: Optional logger instance. If not provided, creates a new logger.
    """
    logger = logger or get_logger("SequentialStrategy")
    stats_by_ticker = (
        combined.groupby("ticker")["signal_type"].value_counts().unstack(fill_value=0).reset_index()
    )
    stats_by_ticker["total"] = stats_by_ticker.get("buy", 0) + stats_by_ticker.get("sell", 0)

    total_signals = len(combined)
    total_buys = (combined["signal_type"] == "buy").sum()
    total_sells = (combined["signal_type"] == "sell").sum()

    logger.info(
        f"Strategy execution complete: {total_signals} total signals "
        f"({total_buys} buys, {total_sells} sells) across "
        f"{combined['ticker'].nunique()} tickers"
    )
