"""Utility functions for backtesting.

This module provides utility functions for backtesting, including data
conversion and queue name constants.
"""

import pandas as pd

BACKTEST_TRADES_QUEUE_NAME = "backtest_trades_queue"
BACKTEST_METRICS_QUEUE_NAME = "backtest_metrics_queue"
BACKTEST_REDIS_TTL = 3600


def dataframe_to_dict(df: pd.DataFrame) -> dict:
    """Convert DataFrame to dictionary format for Redis storage.

    Args:
        df: DataFrame to convert.

    Returns:
        Dictionary representation of the DataFrame.
    """
    df_copy = df.copy()

    if isinstance(df_copy.index, pd.DatetimeIndex):
        datetime_ms = (df_copy.index.astype("int64") // 10**6).tolist()
    elif "datetime" in df_copy.columns:
        datetime_ms = (pd.to_datetime(df_copy["datetime"]).astype("int64") // 10**6).tolist()
        df_copy = df_copy.drop("datetime", axis=1)
    elif "exit_time" in df_copy.columns:
        datetime_ms = (pd.to_datetime(df_copy["exit_time"]).astype("int64") // 10**6).tolist()
    else:
        datetime_ms = (pd.to_datetime(df_copy.index).astype("int64") // 10**6).tolist()

    df_copy = df_copy.reset_index(drop=True)

    for col in df_copy.columns:
        if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
            df_copy[col] = pd.to_datetime(df_copy[col]).astype("int64") // 10**6

    result = df_copy.to_dict("list")
    result["datetime"] = datetime_ms

    return result
