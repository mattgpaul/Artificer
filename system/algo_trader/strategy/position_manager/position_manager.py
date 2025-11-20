"""Position manager for filtering trading signals based on position state.

This module provides functionality to manage position state and filter trading
signals to prevent duplicate entries when a position is already open.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from infrastructure.logging.logger import get_logger


@dataclass
class PositionManagerConfig:
    """Configuration for position manager behavior.

    Attributes:
        allow_scale_in: If True, allows multiple entry signals for the same
            ticker. If False, filters out entry signals when a position is
            already open.
        allow_scale_out: If True, allows partial exits. If False, only full exits allowed.
        close_full_on_exit: If True, first exit signal closes entire position.
    """

    allow_scale_in: bool = False
    allow_scale_out: bool = True
    close_full_on_exit: bool = True

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "PositionManagerConfig":
        """Create PositionManagerConfig from a dictionary.

        Args:
            config_dict: Dictionary containing configuration values.
                Expected keys:
                - allow_scale_in: Boolean indicating if scaling in is allowed.

        Returns:
            PositionManagerConfig instance with values from dictionary.
        """
        return cls(
            allow_scale_in=config_dict.get("allow_scale_in", False),
            allow_scale_out=config_dict.get("allow_scale_out", True),
            close_full_on_exit=config_dict.get("close_full_on_exit", True),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert PositionManagerConfig to dictionary.

        Returns:
            Dictionary representation of the configuration.
        """
        return {
            "allow_scale_in": self.allow_scale_in,
            "allow_scale_out": self.allow_scale_out,
            "close_full_on_exit": self.close_full_on_exit,
        }


class PositionManager:
    """Manages position state and filters trading signals.

    Filters trading signals to prevent duplicate entries when a position is
    already open. Tracks position state per ticker and only allows entry
    signals when no position is open, and exit signals when a position exists.

    Args:
        config: PositionManagerConfig instance controlling behavior.
        logger: Optional logger instance. If not provided, creates a new logger.

    Attributes:
        config: PositionManagerConfig instance.
        logger: Logger instance for this class.
    """

    def __init__(self, config: PositionManagerConfig, logger=None):
        """Initialize PositionManager.

        Args:
            config: PositionManagerConfig instance controlling behavior.
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        self.config = config
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

    def _process_entry_signal(
        self,
        signal_info: dict[str, Any],
        pos: dict[str, Any],
        filtered_indices: list,
    ) -> None:
        """Process an entry signal.

        Args:
            signal_info: Dictionary containing ticker, side, signal_time, and idx.
            pos: Position state dictionary for this ticker.
            filtered_indices: List to append index if signal passes.
        """
        ticker = signal_info["ticker"]
        side = signal_info["side"]
        signal_time = signal_info["signal_time"]
        idx = signal_info["idx"]

        if pos["position_size"] == 0:
            pos["position_size"] = 1.0
            pos["side"] = side
            filtered_indices.append(idx)
        else:
            self.logger.debug(
                f"Filtered entry signal for {ticker} at {signal_time}: "
                f"position already open (side={pos['side']})"
            )

    def _process_exit_signal(
        self,
        signal_info: dict[str, Any],
        pos: dict[str, Any],
        filtered_indices: list,
    ) -> None:
        """Process an exit signal.

        Args:
            signal_info: Dictionary containing ticker, signal_time, and idx.
            pos: Position state dictionary for this ticker.
            filtered_indices: List to append index if signal passes.
        """
        ticker = signal_info["ticker"]
        signal_time = signal_info["signal_time"]
        idx = signal_info["idx"]

        if pos["position_size"] > 0:
            if self.config.close_full_on_exit:
                pos["position_size"] = 0.0
                pos["side"] = None
            elif not self.config.allow_scale_out:
                pos["position_size"] = 0.0
                pos["side"] = None
            filtered_indices.append(idx)
        else:
            self.logger.debug(
                f"Filtered exit signal for {ticker} at {signal_time}: no open position"
            )

    def apply(
        self,
        signals: pd.DataFrame,
        ohlcv_by_ticker: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        """Apply position management filtering to trading signals.

        Filters signals based on position state to prevent duplicate entries.
        When allow_scale_in is False, entry signals are filtered out if a
        position is already open for that ticker.

        Args:
            signals: DataFrame containing trading signals. Must have columns:
                - ticker: Ticker symbol
                - signal_type: Type of signal ('buy' or 'sell')
                - side: Optional side ('LONG' or 'SHORT'), defaults to 'LONG'
                - signal_time: Optional timestamp for sorting signals
            ohlcv_by_ticker: Optional dictionary mapping ticker to OHLCV data.
                Currently unused but reserved for future position sizing logic.

        Returns:
            Filtered DataFrame containing only signals that pass position
            management rules. Returns empty DataFrame if no signals pass.
        """
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
            signal_time = signal.get("signal_time", idx) if has_signal_time_col else idx

            signal_info = {
                "ticker": ticker,
                "side": side,
                "signal_time": signal_time,
                "idx": idx,
            }

            if self._is_entry_signal(side, signal_type):
                self._process_entry_signal(signal_info, pos, filtered_indices)
            elif self._is_exit_signal(side, signal_type):
                self._process_exit_signal(signal_info, pos, filtered_indices)
            else:
                filtered_indices.append(idx)

        if not filtered_indices:
            return pd.DataFrame()

        return signals_sorted.loc[filtered_indices]
