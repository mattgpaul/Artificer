"""Market capitalization calculation utilities.

This module provides functions for calculating market capitalization
from company facts data and OHLCV price data.
"""

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.influx.market_data_influx import MarketDataInflux


def calculate_market_cap(
    company_facts_df: pd.DataFrame,
    ticker: str,
    influx_client: MarketDataInflux | None = None,
) -> pd.DataFrame:
    """Calculate market capitalization for a ticker.

    Calculates market cap by multiplying shares outstanding with the
    closing price from OHLCV data for each period in the company facts DataFrame.

    Args:
        company_facts_df: DataFrame containing company facts with shares_outstanding column.
        ticker: Stock ticker symbol.
        influx_client: Optional MarketDataInflux client. If None, creates a new instance.

    Returns:
        DataFrame with added 'market_cap' column containing calculated market cap values.
    """
    if "shares_outstanding" not in company_facts_df.columns:
        logger = get_logger(__name__)
        logger.warning(f"No shares_outstanding column found for {ticker}")
        company_facts_df["market_cap"] = None
        return company_facts_df

    if influx_client is None:
        influx_client = MarketDataInflux()

    df = company_facts_df.copy()

    start_time = df.index.min().isoformat()
    end_time = df.index.max().isoformat()

    query = (
        f"SELECT time, close FROM ohlcv "
        f"WHERE ticker = '{ticker}' "
        f"AND time >= '{start_time}' "
        f"AND time <= '{end_time}' "
        f"ORDER BY time ASC"
    )

    try:
        ohlcv_df = influx_client.query(query)
        if ohlcv_df is None or (isinstance(ohlcv_df, bool) and not ohlcv_df) or ohlcv_df.empty:
            logger = get_logger(__name__)
            logger.warning(f"No OHLCV data found for {ticker} in date range")
            df["market_cap"] = None
            return df

        if "time" in ohlcv_df.columns:
            ohlcv_df["time"] = pd.to_datetime(ohlcv_df["time"])
            ohlcv_df = ohlcv_df.set_index("time")

        ohlcv_df.index = (
            ohlcv_df.index.tz_localize("UTC") if ohlcv_df.index.tz is None else ohlcv_df.index
        )

        df["market_cap"] = None

        for idx in df.index:
            period_end = idx
            shares = df.loc[idx, "shares_outstanding"]

            if pd.isna(shares):
                continue

            prices_on_or_before = ohlcv_df[ohlcv_df.index <= period_end]
            if not prices_on_or_before.empty:
                close_price = prices_on_or_before["close"].iloc[-1]
            else:
                closest_idx = (ohlcv_df.index - period_end).abs().idxmin()
                close_price = ohlcv_df.loc[closest_idx, "close"]

            if pd.notna(close_price):
                df.loc[idx, "market_cap"] = shares * close_price

        return df

    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to calculate market cap for {ticker}: {e}")
        df["market_cap"] = None
        return df
