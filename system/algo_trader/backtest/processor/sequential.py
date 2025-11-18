"""Sequential processing for backtest execution.

This module provides functionality to execute backtests sequentially,
useful for debugging or when multiprocessing is not desired.
"""

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.processor.worker import backtest_ticker_worker


def process_sequentially(
    worker_args: list[tuple],
    tickers: list[str],
    logger=None,
    hash_id: str | None = None,
    backtest_id: str | None = None,
) -> dict[str, int | str]:
    """Process tickers sequentially without multiprocessing.

    Executes backtest workers one at a time in the current process.
    Useful for debugging or when multiprocessing causes issues.

    Args:
        worker_args: List of argument tuples, one per ticker, for worker processes.
        tickers: List of ticker symbols being processed.
        logger: Optional logger instance. If not provided, creates a new logger.
        hash_id: Optional hash ID for this backtest configuration.
        backtest_id: Optional backtest ID for this backtest run.

    Returns:
        Dictionary containing processing statistics with keys:
        - 'successful': Number of successfully processed tickers
        - 'failed': Number of failed tickers
        - 'total': Total number of tickers processed
        - 'hash_id': Hash ID for this backtest configuration (if provided)
        - 'backtest_id': Backtest ID for this run (if provided)
    """
    logger = logger or get_logger("SequentialProcessor")
    logger.info("Processing tickers sequentially (multiprocessing disabled)...")
    successful = 0
    failed = 0

    for args in worker_args:
        result = backtest_ticker_worker(args)
        if result.get("success", False):
            successful += 1
        else:
            failed += 1

    summary = {"successful": successful, "failed": failed, "total": len(tickers)}
    if hash_id is not None:
        summary["hash_id"] = hash_id
    if backtest_id is not None:
        summary["backtest_id"] = backtest_id

    return summary
