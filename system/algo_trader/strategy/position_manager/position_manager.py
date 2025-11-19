from dataclasses import dataclass
from typing import Any

import pandas as pd

from infrastructure.logging.logger import get_logger


@dataclass
class PositionManagerConfig:
    allow_scale_in: bool = False

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "PositionManagerConfig":
        return cls(
            allow_scale_in=config_dict.get("allow_scale_in", False),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow_scale_in": self.allow_scale_in,
        }


class PositionManager:
    def __init__(self, config: PositionManagerConfig, logger=None):
        self.config = config
        self.logger = logger or get_logger(self.__class__.__name__)

    def apply(
        self,
        signals: pd.DataFrame,
        ohlcv_by_ticker: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        if signals.empty:
            return signals

        if self.config.allow_scale_in:
            return signals

        if "ticker" not in signals.columns or "signal_type" not in signals.columns:
            self.logger.warning(
                "Signals DataFrame missing required columns (ticker, signal_type). "
                "Returning signals unchanged."
            )
            return signals

        filtered_indices = []
        position_state: dict[str, dict[str, Any]] = {}

        has_signal_time_col = "signal_time" in signals.columns
        if has_signal_time_col:
            signals_sorted = signals.sort_values(["ticker", "signal_time"]).copy()
        else:
            signals_sorted = signals.sort_values(["ticker"]).copy()

        for idx, signal in signals_sorted.iterrows():
            ticker = signal["ticker"]
            signal_type = signal["signal_type"]
            side = signal.get("side", "LONG")

            if ticker not in position_state:
                position_state[ticker] = {
                    "position_size": 0.0,
                    "side": None,
                }

            pos = position_state[ticker]

            is_entry = (side == "LONG" and signal_type == "buy") or (
                side == "SHORT" and signal_type == "sell"
            )
            is_exit = (side == "LONG" and signal_type == "sell") or (
                side == "SHORT" and signal_type == "buy"
            )

            signal_time = signal.get("signal_time", idx) if has_signal_time_col else idx

            if is_entry:
                if pos["position_size"] == 0:
                    pos["position_size"] = 1.0
                    pos["side"] = side
                    filtered_indices.append(idx)
                else:
                    self.logger.debug(
                        f"Filtered entry signal for {ticker} at {signal_time}: "
                        f"position already open (side={pos['side']})"
                    )
            elif is_exit:
                if pos["position_size"] > 0:
                    pos["position_size"] = 0.0
                    pos["side"] = None
                    filtered_indices.append(idx)
                else:
                    self.logger.debug(
                        f"Filtered exit signal for {ticker} at {signal_time}: "
                        "no open position"
                    )
            else:
                filtered_indices.append(idx)

        if not filtered_indices:
            return pd.DataFrame()

        return signals_sorted.loc[filtered_indices]

