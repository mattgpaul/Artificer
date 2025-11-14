"""Base class for trading strategy implementations.

This module provides the BaseStrategy abstract class for implementing market
trading strategies that generate buy/sell signals from OHLCV data stored in
InfluxDB and persisting signals back to the database.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

import pandas as pd

from infrastructure.client import Client
from infrastructure.influxdb.influxdb import BatchWriteConfig
from infrastructure.logging.logger import get_logger
from infrastructure.threads.thread_manager import ThreadManager
from system.algo_trader.influx.market_data_influx import MarketDataInflux
from system.algo_trader.strategy.core.data_access import DataAccess
from system.algo_trader.strategy.core.sequential import run_sequential
from system.algo_trader.strategy.core.signal_writer import SignalWriter
from system.algo_trader.strategy.core.threaded import run_threaded

if TYPE_CHECKING:
    from infrastructure.config import ThreadConfig

strategy_write_config = BatchWriteConfig(
    batch_size=50000,
    flush_interval=3000,
    jitter_interval=500,
    retry_interval=8000,
    max_retries=3,
    max_retry_delay=25000,
    exponential_base=2,
)


class BaseStrategy(Client):
    """Base class for market trading strategies.

    Provides infrastructure for querying OHLCV data from InfluxDB, generating
    buy/sell signals via strategy-specific logic, and persisting signals back
    to InfluxDB for analysis and backtesting.

    Subclasses must implement the generate_signals() method to define their
    specific trading logic.

    Attributes:
        logger: Configured logger instance.
        strategy_name: Unique identifier for this strategy.
        influx_client: MarketDataInflux client for database operations.
        thread_manager: Optional ThreadManager for parallel processing.
        strategy_type: Strategy type - 'LONG' or 'SHORT'. Subclasses must set this.
    """

    strategy_type: str = None

    def __init__(
        self,
        strategy_name: str,
        database: str = "algo-trader-database",
        write_config: BatchWriteConfig = strategy_write_config,
        use_threading: bool = False,
        config=None,
        thread_config: ThreadConfig | None = None,
    ):
        """Initialize strategy with InfluxDB connection and optional threading.

        Args:
            strategy_name: Unique name identifying this strategy (used for tagging).
            database: InfluxDB database name (default: "algo-trader-database").
            write_config: Batch write configuration for signal persistence.
            use_threading: Enable ThreadManager for parallel ticker processing.
            config: Optional InfluxDB config. If None, reads from environment.
            thread_config: Optional ThreadConfig for thread management.
                If None and use_threading=True, ThreadManager will auto-create from environment.
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.strategy_name = strategy_name
        self.influx_client = MarketDataInflux(
            database=database, write_config=write_config, config=config
        )
        self.thread_manager = ThreadManager(config=thread_config) if use_threading else None

        self.data_access = DataAccess(self.influx_client, self.strategy_name, self.logger)
        self.signal_writer = SignalWriter(self.influx_client, self.strategy_name, self.logger)

        threading_info = f"threading={use_threading}"
        if use_threading and thread_config:
            threading_info += f", max_threads={thread_config.max_threads}"

        self.logger.debug(
            f"Strategy '{strategy_name}' initialized (database={database}, {threading_info})"
        )

    @abstractmethod
    def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate buy signals from OHLCV data.

        Args:
            ohlcv_data: DataFrame with OHLCV data indexed by datetime.
            ticker: Stock ticker symbol.

        Returns:
            DataFrame with buy signals indexed by timestamp.
        """
        pass

    @abstractmethod
    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate sell signals from OHLCV data.

        Args:
            ohlcv_data: DataFrame with OHLCV data indexed by datetime.
            ticker: Stock ticker symbol.

        Returns:
            DataFrame with sell signals indexed by timestamp.
        """
        pass

    @abstractmethod
    def add_strategy_arguments(self, parser):
        """Add strategy-specific arguments to argument parser.

        Args:
            parser: argparse.ArgumentParser instance to add arguments to.
        """
        pass

    def query_ohlcv(
        self,
        ticker: str,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame | None:
        """Query OHLCV data from InfluxDB for a specific ticker.

        Args:
            ticker: Stock ticker symbol to query.
            start_time: Optional start timestamp (ISO format or InfluxDB time literal).
            end_time: Optional end timestamp (ISO format or InfluxDB time literal).
            limit: Optional maximum number of records to return.

        Returns:
            DataFrame with OHLCV data indexed by time, or None if query fails.
            Columns: time, open, high, low, close, volume, ticker

        Example:
            >>> ohlcv = strategy.query_ohlcv('AAPL', start_time='2024-01-01')
        """
        return self.data_access.query_ohlcv(ticker, start_time, end_time, limit)

    def write_signals(self, signals: pd.DataFrame, ticker: str) -> bool:
        """Write trading signals to InfluxDB strategy table.

        Args:
            signals: DataFrame with signal data indexed by datetime.
                    Must contain at minimum: signal_type, price
                    Optional: confidence, metadata
            ticker: Stock ticker symbol the signals are for.

        Returns:
            True if write succeeded, False otherwise.

        Example:
            >>> signals_df = pd.DataFrame({
            ...     'signal_type': ['buy', 'sell'],
            ...     'price': [150.0, 155.0],
            ...     'confidence': [0.85, 0.92]
            ... }, index=pd.to_datetime(['2024-01-01', '2024-01-02']))
            >>> strategy.write_signals(signals_df, 'AAPL')
        """
        return self.signal_writer.write_signals(signals, ticker)

    def run_strategy(
        self,
        ticker: str,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
        write_signals: bool = True,
    ) -> pd.DataFrame:
        """Execute complete strategy workflow for a single ticker.

        Queries OHLCV data, generates signals, optionally writes to InfluxDB, and returns
        a summary DataFrame.

        Args:
            ticker: Stock ticker symbol to analyze.
            start_time: Optional start timestamp for OHLCV query.
            end_time: Optional end timestamp for OHLCV query.
            limit: Optional limit on OHLCV records to fetch.
            write_signals: Whether to write signals to InfluxDB (default: True).

        Returns:
            DataFrame with signal summary:
                - ticker: Stock symbol
                - signal_type: 'buy' or 'sell'
                - signal_time: Timestamp of signal
                - price: Price at signal
                - Additional columns from generate_signals()

            Empty DataFrame if no signals generated or errors occurred.

        Example:
            >>> summary = strategy.run_strategy('AAPL', start_time='2024-01-01')
        """
        self.logger.debug(f"Running {self.strategy_name} strategy for {ticker}")

        ohlcv_data = self.query_ohlcv(ticker, start_time, end_time, limit)
        if ohlcv_data is None or ohlcv_data.empty:
            self.logger.debug(f"No OHLCV data available for {ticker}")
            return pd.DataFrame()

        try:
            buy_signals = self.buy(ohlcv_data, ticker)
            sell_signals = self.sell(ohlcv_data, ticker)
        except Exception as e:
            self.logger.error(f"Signal generation failed for {ticker}: {e}")
            return pd.DataFrame()

        if not buy_signals.empty:
            buy_signals["signal_type"] = "buy"
            buy_signals["side"] = self.strategy_type if self.strategy_type else "LONG"
        if not sell_signals.empty:
            sell_signals["signal_type"] = "sell"
            sell_signals["side"] = self.strategy_type if self.strategy_type else "LONG"

        if buy_signals.empty and sell_signals.empty:
            self.logger.debug(f"No signals generated for {ticker}")
            return pd.DataFrame()
        elif buy_signals.empty:
            signals = sell_signals
        elif sell_signals.empty:
            signals = buy_signals
        else:
            signals = pd.concat([buy_signals, sell_signals]).sort_index()

        if write_signals:
            write_success = self.write_signals(signals, ticker)
            if not write_success:
                self.logger.warning(
                    f"Failed to write signals for {ticker}, returning summary anyway"
                )

        summary = signals.copy()
        summary["ticker"] = ticker
        summary["signal_time"] = summary.index
        summary = summary.reset_index(drop=True)

        self.logger.debug(
            f"Strategy complete for {ticker}: {len(summary)} signals "
            f"({(summary['signal_type'] == 'buy').sum()} buys, "
            f"{(summary['signal_type'] == 'sell').sum()} sells)"
        )

        return summary

    def run_strategy_multi(
        self,
        tickers: list[str],
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
        write_signals: bool = True,
    ) -> pd.DataFrame:
        """Execute strategy for multiple tickers with optional parallel processing.

        If ThreadManager is enabled, processes tickers in parallel up to the
        configured max_threads limit. Otherwise processes sequentially.

        Args:
            tickers: List of stock ticker symbols to analyze.
            start_time: Optional start timestamp for OHLCV query.
            end_time: Optional end timestamp for OHLCV query.
            limit: Optional limit on OHLCV records per ticker.
            write_signals: Whether to write signals to InfluxDB (default: True).

        Returns:
            DataFrame with combined signal summaries for all tickers.
            Includes statistics: total_signals, buy_signals, sell_signals per ticker.

        Example:
            >>> tickers = ['AAPL', 'MSFT', 'GOOGL']
            >>> results = strategy.run_strategy_multi(tickers, start_time='2024-01-01')
        """
        self.logger.info(
            f"Running {self.strategy_name} for {len(tickers)} tickers "
            f"(threading={'enabled' if self.thread_manager else 'disabled'})"
        )

        if self.thread_manager:
            return run_threaded(
                self,
                tickers,
                start_time,
                end_time,
                limit,
                write_signals,
                self.thread_manager,
                self.logger,
            )
        else:
            return run_sequential(
                self, tickers, start_time, end_time, limit, write_signals, self.logger
            )

    def query_signals(
        self,
        ticker: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        signal_type: str | None = None,
    ) -> pd.DataFrame | None:
        """Query previously generated signals from InfluxDB.

        Args:
            ticker: Optional ticker symbol to filter by.
            start_time: Optional start timestamp.
            end_time: Optional end timestamp.
            signal_type: Optional signal type filter ('buy' or 'sell').

        Returns:
            DataFrame with historical signals, or None if query fails.

        Example:
            >>> buys = strategy.query_signals(ticker='AAPL', signal_type='buy')
        """
        return self.data_access.query_signals(ticker, start_time, end_time, signal_type)

    def close(self) -> None:
        """Close InfluxDB client and cleanup resources."""
        self.influx_client.close()
        self.logger.debug(f"Strategy '{self.strategy_name}' closed")
