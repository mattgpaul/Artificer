"""Data loader for backtest OHLCV data from InfluxDB.

This module provides functionality to load historical OHLCV (Open, High, Low, Close, Volume)
data from InfluxDB for backtesting purposes.
"""

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.influx.market_data_influx import MarketDataInflux


class DataLoader:
    """Loads OHLCV data from InfluxDB for backtesting.

    This class handles querying and loading historical market data from InfluxDB,
    ensuring proper timezone handling and data formatting for backtest execution.

    Args:
        influx_client: InfluxDB client instance for querying market data.
        logger: Optional logger instance. If not provided, creates a new logger.
    """

    def __init__(self, influx_client: MarketDataInflux, logger=None):
        """Initialize DataLoader with InfluxDB client.

        Args:
            influx_client: InfluxDB client instance for querying market data.
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        self.influx_client = influx_client
        self.logger = logger or get_logger(self.__class__.__name__)

    def load_ohlcv_data(
        self, tickers: list[str], start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> dict[str, pd.DataFrame]:
        """Load OHLCV data for multiple tickers.

        Queries InfluxDB for OHLCV data for all specified tickers within the given
        date range. Returns a dictionary mapping ticker symbols to DataFrames.

        Args:
            tickers: List of ticker symbols to load data for.
            start_date: Start date for data query (inclusive).
            end_date: End date for data query (inclusive).

        Returns:
            Dictionary mapping ticker symbols to DataFrames containing OHLCV data.
            DataFrames are indexed by time with UTC timezone.
        """
        self.logger.info(f"Loading OHLCV data for {len(tickers)} tickers")
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        data_cache: dict[str, pd.DataFrame] = {}

        for ticker in tickers:
            query = (
                f"SELECT * FROM ohlcv WHERE ticker = '{ticker}' "
                f"AND time >= '{start_str}' AND time <= '{end_str}' "
                f"ORDER BY time ASC"
            )
            df = self.influx_client.query(query)

            if df is None or (isinstance(df, bool) and not df) or df.empty:
                self.logger.warning(f"No OHLCV data found for {ticker}")
                continue

            if "time" in df.columns:
                df["time"] = pd.to_datetime(df["time"], utc=True)
                df = df.set_index("time")
                if df.index.tz is None:
                    df.index = df.index.tz_localize("UTC")
                else:
                    df.index = df.index.tz_convert("UTC")

            data_cache[ticker] = df
            self.logger.debug(f"Loaded {len(df)} records for {ticker}")

        return data_cache

    def load_ticker_ohlcv_data(
        self, ticker: str, start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> pd.DataFrame | None:
        """Load OHLCV data for a single ticker.

        Queries InfluxDB for OHLCV data for a single ticker within the given
        date range.

        Args:
            ticker: Ticker symbol to load data for.
            start_date: Start date for data query (inclusive).
            end_date: End date for data query (inclusive).

        Returns:
            DataFrame containing OHLCV data indexed by time with UTC timezone,
            or None if no data is found.
        """
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        query = (
            f"SELECT * FROM ohlcv WHERE ticker = '{ticker}' "
            f"AND time >= '{start_str}' AND time <= '{end_str}' "
            f"ORDER BY time ASC"
        )
        df = self.influx_client.query(query)

        if df is None or (isinstance(df, bool) and not df) or df.empty:
            self.logger.warning(f"No OHLCV data found for {ticker}")
            return None

        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], utc=True)
            df = df.set_index("time")
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
            else:
                df.index = df.index.tz_convert("UTC")

        self.logger.debug(f"Loaded {len(df)} records for {ticker}")
        return df
