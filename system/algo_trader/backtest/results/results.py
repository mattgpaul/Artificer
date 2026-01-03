"""Results module for backtest execution.

This module exports the ResultsWriter class for writing backtest results
to Redis queues for later publication to InfluxDB.
"""

from system.algo_trader.backtest.results.writer import ResultsWriter

__all__ = ["ResultsWriter"]
