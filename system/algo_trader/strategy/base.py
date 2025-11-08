"""Base class for trading strategy implementations.

This module provides the BaseStrategy abstract class for implementing market
trading strategies that generate buy/sell signals from OHLCV data stored in
InfluxDB and persist signals back to the database.
"""

from abc import abstractmethod
from datetime import datetime, timezone

import pandas as pd

from infrastructure.client import Client
from infrastructure.influxdb.influxdb import BatchWriteConfig
from infrastructure.logging.logger import get_logger
from infrastructure.threads.thread_manager import ThreadManager
from system.algo_trader.influx.market_data_influx import MarketDataInflux

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
    """

    def __init__(
        self,
        strategy_name: str,
        database: str = "algo-trader-database",
        write_config: BatchWriteConfig = strategy_write_config,
        use_threading: bool = False,
        config=None,
    ):
        """Initialize strategy with InfluxDB connection and optional threading.

        Args:
            strategy_name: Unique name identifying this strategy (used for tagging).
            database: InfluxDB database name (default: "algo-trader-database").
            write_config: Batch write configuration for signal persistence.
            use_threading: Enable ThreadManager for parallel ticker processing.
            config: Optional InfluxDB config. If None, reads from environment.
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.strategy_name = strategy_name
        self.influx_client = MarketDataInflux(
            database=database, write_config=write_config, config=config
        )
        self.thread_manager = ThreadManager() if use_threading else None

        self.logger.info(
            f"Strategy '{strategy_name}' initialized (database={database}, "
            f"threading={use_threading})"
        )

    @abstractmethod
    def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def add_strategy_arguments(self, parser):
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
        # Build SQL query with optional filters
        query = f"SELECT * FROM ohlcv WHERE ticker = '{ticker}'"

        if start_time:
            query += f" AND time >= '{start_time}'"
        if end_time:
            query += f" AND time <= '{end_time}'"

        query += " ORDER BY time ASC"

        if limit:
            query += f" LIMIT {limit}"

        self.logger.debug(f"Querying OHLCV for {ticker}: {query}")

        try:
            df = self.influx_client.query(query)
            if df is None or (isinstance(df, bool) and not df):
                self.logger.warning(f"No OHLCV data found for {ticker}")
                return None

            # Set time as index if it exists
            if "time" in df.columns:
                df["time"] = pd.to_datetime(df["time"])
                df = df.set_index("time")

            self.logger.info(f"Retrieved {len(df)} OHLCV records for {ticker}")
            return df

        except Exception as e:
            self.logger.error(f"Failed to query OHLCV for {ticker}: {e}")
            return None

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
        if signals.empty:
            self.logger.info(f"No signals to write for {ticker}")
            return True

        # Validate required columns
        required_cols = {"signal_type", "price"}
        if not required_cols.issubset(signals.columns):
            missing = required_cols - set(signals.columns)
            self.logger.error(f"Missing required columns: {missing}")
            return False

        # Add metadata columns
        signals_copy = signals.copy()
        signals_copy["ticker"] = ticker
        signals_copy["strategy"] = self.strategy_name
        signals_copy["generated_at"] = datetime.now(timezone.utc).isoformat()

        # Ensure index is datetime with name 'time' for InfluxDB
        if not isinstance(signals_copy.index, pd.DatetimeIndex):
            self.logger.error("Signals DataFrame must have DatetimeIndex")
            return False

        # Reset index to convert to column named 'time'
        signals_copy = signals_copy.reset_index()
        if signals_copy.columns[0] != "time":
            signals_copy = signals_copy.rename(columns={signals_copy.columns[0]: "time"})

        # Convert to milliseconds timestamp for consistency with OHLCV format
        signals_copy["datetime"] = pd.to_datetime(signals_copy["time"]).astype("int64") // 10**6
        signals_copy = signals_copy.drop("time", axis=1)

        # Convert to list of dicts for write method
        signal_records = signals_copy.to_dict("records")

        try:
            success = self.influx_client.write(data=signal_records, ticker=ticker, table="strategy")
            if success:
                self.logger.info(f"Wrote {len(signal_records)} signals for {ticker} to InfluxDB")
            return success
        except Exception as e:
            self.logger.error(f"Failed to write signals for {ticker}: {e}")
            return False

    def run_strategy(
        self,
        ticker: str,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Execute complete strategy workflow for a single ticker.

        Queries OHLCV data, generates signals, writes to InfluxDB, and returns
        a summary DataFrame.

        Args:
            ticker: Stock ticker symbol to analyze.
            start_time: Optional start timestamp for OHLCV query.
            end_time: Optional end timestamp for OHLCV query.
            limit: Optional limit on OHLCV records to fetch.

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
        self.logger.info(f"Running {self.strategy_name} strategy for {ticker}")

        # Query OHLCV data
        ohlcv_data = self.query_ohlcv(ticker, start_time, end_time, limit)
        if ohlcv_data is None or ohlcv_data.empty:
            self.logger.warning(f"No OHLCV data available for {ticker}")
            return pd.DataFrame()

        # Generate buy and sell signals using strategy-specific logic
        try:
            buy_signals = self.buy(ohlcv_data, ticker)
            sell_signals = self.sell(ohlcv_data, ticker)
        except Exception as e:
            self.logger.error(f"Signal generation failed for {ticker}: {e}")
            return pd.DataFrame()

        # Add signal_type to each DataFrame
        if not buy_signals.empty:
            buy_signals["signal_type"] = "buy"
        if not sell_signals.empty:
            sell_signals["signal_type"] = "sell"

        # Combine buy and sell signals
        if buy_signals.empty and sell_signals.empty:
            self.logger.info(f"No signals generated for {ticker}")
            return pd.DataFrame()
        elif buy_signals.empty:
            signals = sell_signals
        elif sell_signals.empty:
            signals = buy_signals
        else:
            signals = pd.concat([buy_signals, sell_signals]).sort_index()

        # Write signals to InfluxDB
        write_success = self.write_signals(signals, ticker)
        if not write_success:
            self.logger.warning(f"Failed to write signals for {ticker}, returning summary anyway")

        # Build summary DataFrame
        summary = signals.copy()
        summary["ticker"] = ticker
        summary["signal_time"] = summary.index
        summary = summary.reset_index(drop=True)

        self.logger.info(
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
    ) -> pd.DataFrame:
        """Execute strategy for multiple tickers with optional parallel processing.

        If ThreadManager is enabled, processes tickers in parallel up to the
        configured max_threads limit. Otherwise processes sequentially.

        Args:
            tickers: List of stock ticker symbols to analyze.
            start_time: Optional start timestamp for OHLCV query.
            end_time: Optional end timestamp for OHLCV query.
            limit: Optional limit on OHLCV records per ticker.

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
            return self._run_threaded(tickers, start_time, end_time, limit)
        else:
            return self._run_sequential(tickers, start_time, end_time, limit)

    def _run_sequential(
        self,
        tickers: list[str],
        start_time: str | None,
        end_time: str | None,
        limit: int | None,
    ) -> pd.DataFrame:
        """Execute strategy sequentially for multiple tickers."""
        all_summaries = []

        for ticker in tickers:
            summary = self.run_strategy(ticker, start_time, end_time, limit)
            if not summary.empty:
                all_summaries.append(summary)

        if not all_summaries:
            self.logger.info("No signals generated for any tickers")
            return pd.DataFrame()

        combined = pd.concat(all_summaries, ignore_index=True)
        self._log_multi_summary(combined)
        return combined

    def _run_threaded(
        self,
        tickers: list[str],
        start_time: str | None,
        end_time: str | None,
        limit: int | None,
    ) -> pd.DataFrame:
        """Execute strategy in parallel using ThreadManager."""

        def process_ticker(ticker: str) -> dict:
            """Thread target for processing a single ticker."""
            try:
                summary = self.run_strategy(ticker, start_time, end_time, limit)
                return {"success": True, "summary": summary}
            except Exception as e:
                self.logger.error(f"Thread failed for {ticker}: {e}")
                return {"success": False, "error": str(e)}

        # Start threads for all tickers (ThreadManager handles batching)
        for ticker in tickers:
            try:
                self.thread_manager.start_thread(
                    target=process_ticker, name=f"strategy-{ticker}", args=(ticker,)
                )
            except RuntimeError as e:
                self.logger.error(f"Failed to start thread for {ticker}: {e}")

        # Wait for all threads to complete
        self.logger.info("Waiting for all strategy threads to complete...")
        self.thread_manager.wait_for_all_threads(timeout=300)

        # Collect results
        all_results = self.thread_manager.get_all_results()
        all_summaries = []

        for _name, result in all_results.items():
            if result and result.get("success"):
                summary = result.get("summary")
                if summary is not None and not summary.empty:
                    all_summaries.append(summary)

        # Cleanup threads
        self.thread_manager.cleanup_dead_threads()

        # Wait for InfluxDB batch writes to complete
        self.influx_client.wait_for_batches(timeout=30)

        if not all_summaries:
            self.logger.info("No signals generated for any tickers")
            return pd.DataFrame()

        combined = pd.concat(all_summaries, ignore_index=True)
        self._log_multi_summary(combined)
        return combined

    def _log_multi_summary(self, combined: pd.DataFrame) -> None:
        """Log summary statistics for multi-ticker strategy execution."""
        stats_by_ticker = (
            combined.groupby("ticker")["signal_type"]
            .value_counts()
            .unstack(fill_value=0)
            .reset_index()
        )
        stats_by_ticker["total"] = stats_by_ticker.get("buy", 0) + stats_by_ticker.get("sell", 0)

        total_signals = len(combined)
        total_buys = (combined["signal_type"] == "buy").sum()
        total_sells = (combined["signal_type"] == "sell").sum()

        self.logger.info(
            f"Strategy execution complete: {total_signals} total signals "
            f"({total_buys} buys, {total_sells} sells) across "
            f"{combined['ticker'].nunique()} tickers"
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
        query = f"SELECT * FROM strategy WHERE strategy = '{self.strategy_name}'"

        if ticker:
            query += f" AND ticker = '{ticker}'"
        if start_time:
            query += f" AND time >= '{start_time}'"
        if end_time:
            query += f" AND time <= '{end_time}'"
        if signal_type:
            query += f" AND signal_type = '{signal_type}'"

        query += " ORDER BY time DESC"

        self.logger.debug(f"Querying signals: {query}")

        try:
            df = self.influx_client.query(query)
            if df is None or (isinstance(df, bool) and not df):
                self.logger.info("No signals found matching criteria")
                return None

            self.logger.info(f"Retrieved {len(df)} historical signals")
            return df

        except Exception as e:
            self.logger.error(f"Failed to query signals: {e}")
            return None

    def close(self) -> None:
        """Close InfluxDB client and cleanup resources."""
        self.influx_client.close()
        self.logger.info(f"Strategy '{self.strategy_name}' closed")
