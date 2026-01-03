"""Utilities for fundamentals data processing.

This module provides helper functions for converting dataframes and
displaying summary statistics.
"""

import pandas as pd

FUNDAMENTALS_QUEUE_NAME = "fundamentals_queue"
FUNDAMENTALS_STATIC_QUEUE_NAME = "fundamentals_static_queue"
FUNDAMENTALS_REDIS_TTL = 3600


def dataframe_to_dict(df: pd.DataFrame) -> dict:
    """Convert pandas DataFrame to dictionary format for Redis storage.

    Args:
        df: DataFrame to convert. Must have datetime index or 'time' column.

    Returns:
        Dictionary with column data as lists and 'datetime' key containing
        millisecond timestamps.
    """
    df_copy = df.copy()

    if isinstance(df_copy.index, pd.DatetimeIndex):
        datetime_ms = (df_copy.index.astype("int64") // 10**6).tolist()
    elif "time" in df_copy.columns:
        datetime_ms = (pd.to_datetime(df_copy["time"]).astype("int64") // 10**6).tolist()
        df_copy = df_copy.drop("time", axis=1)
    else:
        datetime_ms = (pd.to_datetime(df_copy.index).astype("int64") // 10**6).tolist()

    df_copy = df_copy.reset_index(drop=True)
    result = df_copy.to_dict("list")
    result["datetime"] = datetime_ms

    return result


def print_summary(stats: dict, write: bool) -> None:
    """Print summary statistics for fundamentals data fetching.

    Args:
        stats: Dictionary containing statistics (total, successful, failed,
            static_rows, time_series_rows, market_cap_rows).
        write: If True, indicates data was written. If False, dry-run mode.
    """
    print(f"\n{'=' * 50}")
    print("Fundamentals Data Fetching Summary")
    print(f"{'=' * 50}")
    print(f"Total Tickers: {stats['total']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Static Data Rows: {stats['static_rows']}")
    print(f"Time Series Rows: {stats['time_series_rows']}")
    print(f"Market Cap Rows: {stats['market_cap_rows']}")
    if write:
        print(f"Time Series Queue: {FUNDAMENTALS_QUEUE_NAME}")
        print(f"Static Data Queue: {FUNDAMENTALS_STATIC_QUEUE_NAME}")
        print(f"Redis TTL: {FUNDAMENTALS_REDIS_TTL}s")
        print("\nTime series data will be published to InfluxDB by the influx-publisher service.")
        print("Static data will be written to MySQL by the mysql-daemon service.")
    else:
        print("\nDry-run mode: No data was written to MySQL or Redis.")
    print(f"{'=' * 50}\n")
