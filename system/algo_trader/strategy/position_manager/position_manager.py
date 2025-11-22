from typing import Any

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.position_manager.rules.base import (
    PositionRuleContext,
    PositionState,
)
from system.algo_trader.strategy.position_manager.rules.pipeline import PositionRulePipeline


class PositionManager:
    def __init__(self, pipeline: PositionRulePipeline, logger=None):
        self.pipeline = pipeline
        self.logger = logger or get_logger(self.__class__.__name__)

    def _is_entry_signal(self, side: str, signal_type: str) -> bool:
        """Check if signal is an entry signal.

        Args:
            side: Position side ('LONG' or 'SHORT').
            signal_type: Signal type ('buy' or 'sell').

        Returns:
            True if signal is an entry signal, False otherwise.
        """
        return (side == "LONG" and signal_type == "buy") or (
            side == "SHORT" and signal_type == "sell"
        )

    def _is_exit_signal(self, side: str, signal_type: str) -> bool:
        """Check if signal is an exit signal.

        Args:
            side: Position side ('LONG' or 'SHORT').
            signal_type: Signal type ('buy' or 'sell').

        Returns:
            True if signal is an exit signal, False otherwise.
        """
        return (side == "LONG" and signal_type == "sell") or (
            side == "SHORT" and signal_type == "buy"
        )


    def apply(
        self,
        signals: pd.DataFrame,
        ohlcv_by_ticker: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        if signals.empty:
            return signals

        if "ticker" not in signals.columns or "signal_type" not in signals.columns:
            self.logger.warning(
                "Signals DataFrame missing required columns (ticker, signal_type). "
                "Returning signals unchanged."
            )
            return signals

        filtered_indices = []
        position_state: dict[str, PositionState] = {}

        has_signal_time_col = "signal_time" in signals.columns
        if has_signal_time_col:
            signals_sorted = signals.sort_values(["ticker", "signal_time"]).copy()
        else:
            signals_sorted = signals.sort_values(["ticker"]).copy()

        for idx, signal_row in signals_sorted.iterrows():
            ticker = signal_row["ticker"]
            signal_type = signal_row["signal_type"]
            side = signal_row.get("side", "LONG")

            if ticker not in position_state:
                position_state[ticker] = PositionState()

            pos = position_state[ticker]
            signal_time = signal_row.get("signal_time", idx) if has_signal_time_col else idx

            signal_dict = signal_row.to_dict()

            if self._is_entry_signal(side, signal_type):
                context = PositionRuleContext(signal_dict, pos, ohlcv_by_ticker)
                if self.pipeline.decide_entry(context):
                    if pos.size == 0:
                        pos.size = 1.0
                        pos.side = side
                        entry_price = signal_dict.get("price") or signal_dict.get("close")
                        if entry_price is not None:
                            try:
                                pos.entry_price = float(entry_price)
                            except (ValueError, TypeError):
                                pass
                        filtered_indices.append(idx)
                    else:
                        self.logger.debug(
                            f"Filtered entry signal for {ticker} at {signal_time}: "
                            f"position already open (side={pos.side})"
                        )
                else:
                    self.logger.debug(
                        f"Filtered entry signal for {ticker} at {signal_time}: "
                        "rejected by position rules"
                    )
            elif self._is_exit_signal(side, signal_type):
                if pos.size > 0:
                    context = PositionRuleContext(signal_dict, pos, ohlcv_by_ticker)
                    exit_fraction = self.pipeline.decide_exit(context)
                    if exit_fraction > 0.0:
                        pos.size = max(0.0, pos.size - exit_fraction)
                        if pos.size <= 0.0:
                            pos.size = 0.0
                            pos.side = None
                            pos.entry_price = None
                        filtered_indices.append(idx)
                        if exit_fraction < 1.0:
                            signals_sorted.at[idx, "fraction"] = exit_fraction
                    else:
                        self.logger.debug(
                            f"Filtered exit signal for {ticker} at {signal_time}: "
                            "no exit rule triggered"
                        )
                else:
                    self.logger.debug(
                        f"Filtered exit signal for {ticker} at {signal_time}: no open position"
                    )
            else:
                filtered_indices.append(idx)

        if not filtered_indices:
            return pd.DataFrame()

        return signals_sorted.loc[filtered_indices]
