"""InfluxDB client for market data persistence.

This module provides the MarketDataInflux class for storing market data
time-series in InfluxDB with batch write support and pandas DataFrame
integration.
"""

import pandas as pd

from infrastructure.influxdb.influxdb import BaseInfluxDBClient, BatchWriteConfig
from infrastructure.logging.logger import get_logger

market_write_config = BatchWriteConfig(
    batch_size=10000,
    flush_interval=10_00,
    jitter_interval=2_000,
    retry_interval=15_000,
    max_retries=5,
    max_retry_delay=30_000,
    exponential_base=2,
)


class MarketDataInflux(BaseInfluxDBClient):
    """InfluxDB client for storing and querying market data time series.

    Handles formatting and storage of stock price history data in InfluxDB,
    including data transformation to DataFrame format and batch writing with
    retry logic for market data workloads.

    Attributes:
        logger: Configured logger instance.
        database: Target InfluxDB database name.
        write_config: Batch write configuration for market data.
    """

    def __init__(
        self,
        database: str = "historical_market_data",
        write_config=market_write_config,
        config=None,
    ):
        """Initialize market data InfluxDB client.

        Args:
            database: Target database name for market data storage.
            write_config: Batch write configuration optimized for market data.
            config: Optional InfluxDBConfig. If None, reads from environment.
        """
        super().__init__(database=database, write_config=write_config, config=config)
        self.logger = get_logger(self.__class__.__name__)

    def _format_stock_data(self, data: dict | list, ticker: str) -> pd.DataFrame:
        """Format stock data for InfluxDB write operations.

        Converts market data dictionary or list to pandas DataFrame with datetime
        index. Handles empty data and missing datetime columns.

        Args:
            data: Dictionary or list containing market data with datetime and OHLCV fields.
            ticker: Stock ticker symbol for logging purposes.

        Returns:
            DataFrame with datetime index and OHLCV columns (datetime column removed).

        Raises:
            ValueError: If datetime column is missing from data.
        """
        self.logger.debug(f"Formatting {ticker}")
        # TODO: datetime probably needs formatting
        df = pd.DataFrame(data)

        if df.empty:
            self.logger.warning(f"Empty DataFrame for {ticker} - cannot format")
            return df

        if "datetime" not in df.columns:
            self.logger.error(f"No 'datetime' column in data for {ticker}")
            raise ValueError(f"No 'datetime' column found in data for {ticker}")

        df = df.set_index(pd.to_datetime(df["datetime"], unit="ms", utc=True))
        df = df.drop("datetime", axis=1)
        return df

    def write(
        self, data: dict, ticker: str, table: str, tag_columns: list[str] | None = None
    ) -> bool:
        """Write market data to InfluxDB.

        Args:
            data: Dictionary containing market data with datetime and OHLCV fields.
            ticker: Stock ticker symbol to tag data with.
            table: Target measurement/table name in InfluxDB.
            tag_columns: List of column names to use as tags. Defaults to ["ticker"].

        Returns:
            True if write succeeded, False otherwise.
        """
        # Format data (works for any table - stock, ohlcv, etc.)
        df = self._format_stock_data(data, ticker)

        # Add ticker as a tag column
        df["ticker"] = ticker

        if tag_columns is None:
            tag_columns = ["ticker"]

        # Clean and validate tag columns
        for col in tag_columns:
            if col not in df.columns:
                self.logger.warning(f"Tag column '{col}' not found in DataFrame for {ticker}")
                continue

            # Replace NaN values with placeholder for tags (InfluxDB rejects empty tag values)
            nan_mask = df[col].isna()
            if nan_mask.any():
                placeholder = "unknown" if col != "ticker" else ticker
                df.loc[nan_mask, col] = placeholder

            # Convert to string and clean invalid string representations
            df[col] = df[col].astype(str)
            df[col] = df[col].replace(
                ["nan", "None", "<NA>", "NaN", "null"], "unknown", regex=False
            )

            # Replace any remaining empty strings with placeholder (InfluxDB rejects empty tags)
            empty_mask = df[col] == ""
            if empty_mask.any():
                placeholder = "unknown" if col != "ticker" else ticker
                df.loc[empty_mask, col] = placeholder

        # Ensure all numeric columns are float64 (InfluxDB prefers floats)
        for col in df.columns:
            if col not in tag_columns and pd.api.types.is_integer_dtype(df[col]):
                df[col] = df[col].astype("float64")

        # Fill NaN values in non-tag columns
        non_tag_cols = [col for col in df.columns if col not in tag_columns]
        if non_tag_cols:
            df[non_tag_cols] = df[non_tag_cols].fillna(0)

        try:
            # Increment pending batch counter before write
            self._callback.increment_pending()

            # CRITICAL FIX: InfluxDB client library has a bug with DataFrame conversion
            # when using multiple tags. Use Point API to bypass the buggy DataFrame write path.
            from influxdb_client_3 import Point

            points = []
            for idx, row in df.iterrows():
                point = Point(table)

                # Add tags - ensure they're strings and non-empty
                for tag_col in tag_columns:
                    if tag_col in row.index:
                        tag_value = str(row[tag_col])
                        # Skip empty or invalid tag values
                        if tag_value and tag_value not in ["nan", "None", "<NA>", "NaN", "null", ""]:
                            point = point.tag(tag_col, tag_value)

                # Add fields - all non-tag columns
                for col in df.columns:
                    if col not in tag_columns:
                        value = row[col]
                        # Skip NaN values
                        if pd.isna(value):
                            continue
                        # Add as appropriate type
                        if isinstance(value, (int, float)):
                            point = point.field(col, float(value))
                        elif isinstance(value, str):
                            if value and value not in ["nan", "None", "<NA>", "NaN", "null"]:
                                point = point.field(col, value)
                        else:
                            point = point.field(col, str(value))

                # Set timestamp from index
                if isinstance(idx, pd.Timestamp):
                    point = point.time(idx.value)  # nanoseconds

                points.append(point)

            # Write points directly (bypasses DataFrame conversion bug)
            self.client.write(records=points)

            return True
        except Exception as e:
            # Decrement on exception since write failed
            with self._callback._lock:
                self._callback._pending_batches -= 1
            self.logger.error(f"Failed to write data for {ticker}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def query(self, query: str):
        """Query market data from InfluxDB using SQL.

        Args:
            query: SQL query string to execute against InfluxDB.

        Returns:
            DataFrame containing query results, or None if query fails.
        """
        self.logger.debug("Getting data")
        try:
            df = self.client.query(query=query, language="sql", mode="pandas")
        except Exception as e:
            self.logger.error(f"Failed to retrieve query: {e}")
            df = False

        return df
