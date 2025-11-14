from dataclasses import dataclass

import pandas as pd


@dataclass
class ExecutionConfig:
    slippage_bps: float = 5.0
    commission_per_share: float = 0.005
    use_limit_orders: bool = False
    fill_delay_minutes: int = 0


class ExecutionSimulator:
    def __init__(self, config: ExecutionConfig):
        self.config = config

    def apply_execution(self, trades: pd.DataFrame, ohlcv_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
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

                entry_fill = self._calculate_fill_price(entry_price, entry_time, ticker_data, "entry")
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

    def _calculate_fill_price(
        self,
        signal_price: float,
        timestamp: pd.Timestamp,
        ohlcv_data: pd.DataFrame,
        side: str,
    ) -> float:
        if ohlcv_data.empty:
            return signal_price

        # Ensure timestamp is timezone-aware (UTC) for comparison
        if timestamp.tz is None:
            timestamp = timestamp.tz_localize("UTC")
        else:
            timestamp = timestamp.tz_convert("UTC")

        # Ensure index is timezone-aware (UTC) for comparison
        # Work with a copy to avoid modifying original data
        ohlcv_utc = ohlcv_data.copy()
        if ohlcv_utc.index.tz is None:
            ohlcv_utc.index = ohlcv_utc.index.tz_localize("UTC")
        else:
            ohlcv_utc.index = ohlcv_utc.index.tz_convert("UTC")

        # Find the bar at or before the signal timestamp
        if timestamp not in ohlcv_utc.index:
            closest_idx = ohlcv_utc.index[ohlcv_utc.index <= timestamp]
            if len(closest_idx) == 0:
                return signal_price
            signal_bar_time = closest_idx[-1]
        else:
            signal_bar_time = timestamp

        # FIX FORWARD-LOOKING BIAS: Use the NEXT bar after signal detection for execution
        # Signal detected at time T, but we can't execute until time T+1
        next_bars = ohlcv_utc.index[ohlcv_utc.index > signal_bar_time]
        if len(next_bars) == 0:
            # No future bar available, use signal bar (edge case at end of data)
            execution_bar_time = signal_bar_time
        else:
            execution_bar_time = next_bars[0]

        # Use the execution bar for price lookup
        bar = ohlcv_utc.loc[execution_bar_time]

        if self.config.use_limit_orders:
            if side == "entry":
                fill_price = bar["open"]
            else:
                fill_price = bar["open"]
        else:
            if side == "entry":
                fill_price = bar["close"]
            else:
                fill_price = bar["close"]

        slippage_multiplier = 1 + (self.config.slippage_bps / 10000)
        if side == "entry":
            fill_price = fill_price * slippage_multiplier
        else:
            fill_price = fill_price * (1 - (self.config.slippage_bps / 10000))

        return round(fill_price, 4)

