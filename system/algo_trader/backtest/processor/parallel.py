"""Parallel processing for backtest execution.

This module provides functionality to execute backtests in parallel using
multiprocessing for improved performance.
"""

import multiprocessing

from infrastructure.config import ProcessConfig
from infrastructure.logging.logger import get_logger
from infrastructure.multiprocess.process_manager import ProcessManager
from system.algo_trader.backtest.processor.worker import backtest_ticker_worker


def process_in_parallel(
    worker_args: list[tuple],
    tickers: list[str],
    max_processes: int | None,
    logger=None,
    hash_id: str | None = None,
    backtest_id: str | None = None,
) -> dict[str, int | str]:
    """Process tickers in parallel using multiprocessing.

    Executes backtest workers in parallel across multiple processes for
    improved performance when processing many tickers.

    Args:
        worker_args: List of argument tuples, one per ticker, for worker processes.
        tickers: List of ticker symbols being processed.
        max_processes: Maximum number of parallel processes. If None, uses CPU count - 2.
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
    logger = logger or get_logger("ParallelProcessor")
    process_config = ProcessConfig(max_processes=max_processes)
    process_manager = ProcessManager(config=process_config)

    max_processes = process_config.max_processes or max(1, multiprocessing.cpu_count() - 2)
    if len(tickers) > max_processes:
        logger.info(
            f"Starting multiprocessing with {len(tickers)} tickers "
            f"using {max_processes} processes "
            f"(batching: {len(tickers)} tickers will be processed "
            f"in batches of {max_processes})"
        )
    else:
        logger.info(
            f"Starting multiprocessing with {len(tickers)} tickers using {max_processes} processes"
        )

    results_list = process_manager.map(backtest_ticker_worker, worker_args)
    process_manager.close_pool()

    successful = sum(1 for r in results_list if r.get("success", False))
    failed = len(results_list) - successful

    summary = {"successful": successful, "failed": failed, "total": len(tickers)}
    if hash_id is not None:
        summary["hash_id"] = hash_id
    if backtest_id is not None:
        summary["backtest_id"] = backtest_id

    return summary
