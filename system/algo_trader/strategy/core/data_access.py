"""Data access layer for strategy execution.

This module provides functionality to query OHLCV data and trading signals
from InfluxDB for strategy execution.
"""

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.influx.market_data_influx import MarketDataInflux


class DataAccess:
    """Provides data access methods for strategy execution.

    Handles querying OHLCV market data and historical trading signals
    from InfluxDB for use by trading strategies.

    Args:
        influx_client: InfluxDB client instance for querying data.
        strategy_name: Name of the strategy using this data access.
        logger: Optional logger instance. If not provided, creates a new logger.
    """

    def __init__(self, influx_client: MarketDataInflux, strategy_name: str, logger=None):
        """Initialize DataAccess with InfluxDB client.

        Args:
            influx_client: InfluxDB client instance for querying data.
            strategy_name: Name of the strategy using this data access.
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        self.influx_client = influx_client
        self.strategy_name = strategy_name
        self.logger = logger or get_logger(self.__class__.__name__)

    def query_ohlcv(
        self,
        ticker: str,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame | None:
        """Query OHLCV data from InfluxDB.

        Retrieves historical OHLCV (Open, High, Low, Close, Volume) data
        for a ticker with optional time range and limit.

        Args:
            ticker: Ticker symbol to query data for.
            start_time: Optional start time for data query (ISO format string).
            end_time: Optional end time for data query (ISO format string).
            limit: Optional limit on number of records to return.

        Returns:
            DataFrame containing OHLCV data indexed by time, or None if no data found.
        """
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

            if "time" in df.columns:
                df["time"] = pd.to_datetime(df["time"])
                df = df.set_index("time")

            self.logger.debug(f"Retrieved {len(df)} OHLCV records for {ticker}")
            return df

        except Exception as e:
            self.logger.error(f"Failed to query OHLCV for {ticker}: {e}")
            return None

    def query_signals(
        self,
        ticker: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        signal_type: str | None = None,
    ) -> pd.DataFrame | None:
        """Query historical trading signals from InfluxDB.

        Retrieves previously generated trading signals for the strategy
        with optional filtering by ticker, time range, and signal type.

        Args:
            ticker: Optional ticker symbol to filter signals.
            start_time: Optional start time for signal query (ISO format string).
            end_time: Optional end time for signal query (ISO format string).
            signal_type: Optional signal type to filter ('buy' or 'sell').

        Returns:
            DataFrame containing historical signals, or None if no signals found.
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
