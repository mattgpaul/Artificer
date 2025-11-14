"""Execution simulation for backtesting.

This module provides execution simulation functionality, including:
- ExecutionConfig: Configuration for execution simulation
- ExecutionSimulator: Simulates trade execution with slippage and commissions
"""

from dataclasses import dataclass

import pandas as pd


@dataclass
class ExecutionConfig:
    """Configuration for execution simulation.

    Attributes:
        slippage_bps: Slippage in basis points.
        commission_per_share: Commission per share.
        use_limit_orders: Whether to use limit orders.
        fill_delay_minutes: Fill delay in minutes.
    """

    slippage_bps: float = 5.0
    commission_per_share: float = 0.005
    use_limit_orders: bool = False
    fill_delay_minutes: int = 0


class ExecutionSimulator:
    """Simulates trade execution with slippage and commissions.

    Args:
        config: Execution configuration.
    """

    def __init__(self, config: ExecutionConfig) -> None:
        """Initialize execution simulator.

        Args:
            config: Execution configuration.
        """
        self.config = config

    def apply_execution(
        self, trades: pd.DataFrame, ohlcv_data: dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """Apply execution simulation to trades.

        Args:
            trades: DataFrame containing trade signals.
            ohlcv_data: Dictionary mapping tickers to OHLCV DataFrames.

        Returns:
            DataFrame with executed trades including fill prices and PnL.
        """
        if trades.empty:
            return trades

        executed_trades = trades.copy()

        for idx, trade in executed_trades.iterrows():
            ticker = trade["ticker"]
            entry_price = trade["entry_price"]
            exit_price = trade["exit_price"]

            if ticker in ohlcv_data:
                ticker_data = ohlcv_data[ticker]
                entry_time = trade["entry_time"]
                exit_time = trade["exit_time"]

                entry_fill = self._calculate_fill_price(
                    entry_price, entry_time, ticker_data, "entry"
                )
                exit_fill = self._calculate_fill_price(exit_price, exit_time, ticker_data, "exit")

                executed_trades.at[idx, "entry_price"] = entry_fill
                executed_trades.at[idx, "exit_price"] = exit_fill

                shares = executed_trades.at[idx, "shares"]
                if trade["side"] == "LONG":
                    gross_pnl = shares * (exit_fill - entry_fill)
                else:
                    gross_pnl = shares * (entry_fill - exit_fill)

                commission = (shares * self.config.commission_per_share) * 2
                net_pnl = gross_pnl - commission

                executed_trades.at[idx, "gross_pnl"] = gross_pnl
                executed_trades.at[idx, "net_pnl"] = net_pnl
                executed_trades.at[idx, "commission"] = commission
                executed_trades.at[idx, "gross_pnl_pct"] = (gross_pnl / (shares * entry_fill)) * 100
                executed_trades.at[idx, "net_pnl_pct"] = (net_pnl / (shares * entry_fill)) * 100

        return executed_trades

    def _normalize_timestamp(self, timestamp: pd.Timestamp) -> pd.Timestamp:
        """Normalize timestamp to UTC timezone.

        Args:
            timestamp: Timestamp to normalize.

        Returns:
            UTC timezone-aware timestamp.
        """
        if timestamp.tz is None:
            return timestamp.tz_localize("UTC")
        return timestamp.tz_convert("UTC")

    def _normalize_ohlcv_timezone(self, ohlcv_data: pd.DataFrame) -> pd.DataFrame:
        """Normalize OHLCV DataFrame index to UTC timezone.

        Args:
            ohlcv_data: DataFrame with time index.

        Returns:
            DataFrame with UTC timezone-aware index.
        """
        ohlcv_utc = ohlcv_data.copy()
        if ohlcv_utc.index.tz is None:
            ohlcv_utc.index = ohlcv_utc.index.tz_localize("UTC")
        else:
            ohlcv_utc.index = ohlcv_utc.index.tz_convert("UTC")
        return ohlcv_utc

    def _find_execution_bar_time(
        self, timestamp: pd.Timestamp, ohlcv_utc: pd.DataFrame
    ) -> pd.Timestamp:
        """Find execution bar time for a given timestamp.

        Args:
            timestamp: Signal timestamp.
            ohlcv_utc: OHLCV data with UTC timezone-aware index.

        Returns:
            Execution bar timestamp.
        """
        if timestamp not in ohlcv_utc.index:
            closest_idx = ohlcv_utc.index[ohlcv_utc.index <= timestamp]
            if len(closest_idx) == 0:
                return timestamp
            signal_bar_time = closest_idx[-1]
        else:
            signal_bar_time = timestamp

        # FIX FORWARD-LOOKING BIAS: Use the NEXT bar after signal detection for execution
        # Signal detected at time T, but we can't execute until time T+1
        next_bars = ohlcv_utc.index[ohlcv_utc.index > signal_bar_time]
        if len(next_bars) == 0:
            return signal_bar_time
        return next_bars[0]

    def _get_base_fill_price(self, bar: pd.Series, side: str) -> float:
        """Get base fill price from bar data.

        Args:
            bar: OHLCV bar data.
            side: Trade side ("entry" or "exit").

        Returns:
            Base fill price before slippage.
        """
        if self.config.use_limit_orders:
            return bar["open"]
        return bar["close"]

    def _apply_slippage(self, fill_price: float, side: str) -> float:
        """Apply slippage to fill price.

        Args:
            fill_price: Base fill price.
            side: Trade side ("entry" or "exit").

        Returns:
            Fill price with slippage applied.
        """
        slippage_multiplier = 1 + (self.config.slippage_bps / 10000)
        if side == "entry":
            return fill_price * slippage_multiplier
        return fill_price * (1 - (self.config.slippage_bps / 10000))

    def _calculate_fill_price(
        self,
        signal_price: float,
        timestamp: pd.Timestamp,
        ohlcv_data: pd.DataFrame,
        side: str,
    ) -> float:
        """Calculate fill price for a trade signal.

        Args:
            signal_price: Original signal price.
            timestamp: Signal timestamp.
            ohlcv_data: OHLCV data for price lookup.
            side: Trade side ("entry" or "exit").

        Returns:
            Calculated fill price with slippage.
        """
        if ohlcv_data.empty:
            return signal_price

        timestamp = self._normalize_timestamp(timestamp)
        ohlcv_utc = self._normalize_ohlcv_timezone(ohlcv_data)

        execution_bar_time = self._find_execution_bar_time(timestamp, ohlcv_utc)
        bar = ohlcv_utc.loc[execution_bar_time]

        fill_price = self._get_base_fill_price(bar, side)
        fill_price = self._apply_slippage(fill_price, side)

        return round(fill_price, 4)
