"""Sequential processing for backtest execution.

This module provides functionality to execute backtests sequentially,
useful for debugging or when multiprocessing is not desired.
"""

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.processor.worker import backtest_ticker_worker


def process_sequentially(
    worker_args: list[tuple], tickers: list[str], logger=None
) -> dict[str, int]:
    """Process tickers sequentially without multiprocessing.

    Executes backtest workers one at a time in the current process.
    Useful for debugging or when multiprocessing causes issues.

    Args:
        worker_args: List of argument tuples, one per ticker, for worker processes.
        tickers: List of ticker symbols being processed.
        logger: Optional logger instance. If not provided, creates a new logger.

    Returns:
        Dictionary containing processing statistics with keys:
        - 'successful': Number of successfully processed tickers
        - 'failed': Number of failed tickers
        - 'total': Total number of tickers processed
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

    return {"successful": successful, "failed": failed, "total": len(tickers)}
