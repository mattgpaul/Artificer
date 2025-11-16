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

    Handles NaN values by dropping entirely NaN columns and converting NaN values
    in string columns to empty strings to prevent InfluxDB line protocol errors.

    Args:
        df: DataFrame to convert.

    Returns:
        Dictionary representation of the DataFrame.
    """
    df_copy = df.copy()

    # Drop columns that are entirely NaN before processing
    cols_to_drop = [col for col in df_copy.columns if df_copy[col].isna().all()]
    if cols_to_drop:
        df_copy = df_copy.drop(columns=cols_to_drop)

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

    # Handle datetime columns
    for col in df_copy.columns:
        if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
            df_copy[col] = pd.to_datetime(df_copy[col]).astype("int64") // 10**6

    # Handle NaN values in string columns - convert to empty strings
    # This prevents "nan" strings from appearing in InfluxDB line protocol
    for col in df_copy.columns:
        if df_copy[col].dtype == "object":
            # Replace NaN with empty string for string columns
            nan_mask = df_copy[col].isna()
            if nan_mask.any():
                df_copy.loc[nan_mask, col] = ""
        elif pd.api.types.is_numeric_dtype(df_copy[col]):
            # For numeric columns, replace NaN with 0
            nan_mask = df_copy[col].isna()
            if nan_mask.any():
                df_copy.loc[nan_mask, col] = 0

    result = df_copy.to_dict("list")
    result["datetime"] = datetime_ms

    return result
