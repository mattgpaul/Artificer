"""Progress bar utilities for backtest execution."""

import multiprocessing
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING

from tqdm import tqdm

if TYPE_CHECKING:
    from collections.abc import Iterator


def _get_process_position() -> int | None:
    """Get the position for this process's progress bar.

    In multiprocessing mode, each worker process gets a unique position
    so progress bars don't overwrite each other.

    Returns:
        Position index for the progress bar, or None if not in multiprocessing
    """
    try:
        current_process = multiprocessing.current_process()
        if current_process.name == "MainProcess":
            return None

        # Extract process number from name (e.g., "ForkProcess-1" -> 1)
        # Or use a hash of the process name for consistent positioning
        process_name = current_process.name
        if "-" in process_name:
            try:
                # Try to extract numeric ID
                process_id = int(process_name.split("-")[-1])
                return process_id - 1  # 0-indexed
            except ValueError:
                pass

        # Fallback: use hash of process name
        return hash(process_name) % 10
    except Exception:
        return None


@contextmanager
def ticker_progress_bar(ticker: str, total_steps: int) -> "Iterator[tqdm | None]":
    """Create a progress bar for a ticker's backtest execution.

    In multiprocessing mode, each worker gets its own progress bar position
    to avoid conflicts.

    Args:
        ticker: The ticker symbol being processed
        total_steps: Total number of time steps to process

    Yields:
        A tqdm progress bar instance that can be updated, or None if disabled
    """
    # Check if stdout is a TTY
    if not sys.stdout.isatty():
        yield None
        return

    # Get position for this process
    position = _get_process_position()

    pbar = tqdm(
        total=total_steps,
        desc=f"{ticker:6s}",
        unit="step",
        leave=False,
        ncols=100,
        file=sys.stdout,
        dynamic_ncols=True,
        position=position,
        mininterval=0.5,  # Update at most twice per second
        maxinterval=1.0,
    )
    try:
        yield pbar
    finally:
        pbar.close()
