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

    def _apply_for_ticker_signals_only(
        self,
        signals_for_ticker: pd.DataFrame,
        position: PositionState,
    ) -> list[dict[str, Any]]:
        if signals_for_ticker.empty:
            return []

        out_rows: list[dict[str, Any]] = []
        has_signal_time_col = "signal_time" in signals_for_ticker.columns

        for idx, signal_row in signals_for_ticker.iterrows():
            signal_dict = signal_row.to_dict()
            side = signal_dict.get("side", "LONG")
            signal_type = signal_dict.get("signal_type", "")

            emitted = self._process_strategy_signal(signal_dict, position, {})
            if emitted is not None:
                if not has_signal_time_col:
                    emitted["signal_time"] = idx
                out_rows.append(emitted)

        return out_rows

    def _apply_for_ticker_with_bars(
        self,
        ticker: str,
        signals_for_ticker: pd.DataFrame,
        ohlcv: pd.DataFrame,
        position: PositionState,
    ) -> list[dict[str, Any]]:
        sig = signals_for_ticker.sort_values("signal_time").copy() if not signals_for_ticker.empty else pd.DataFrame()
        sig_idx = 0
        sig_rows = list(sig.to_dict("records")) if not sig.empty else []
        n_signals = len(sig_rows)

        out: list[dict[str, Any]] = []

        for ts, bar in ohlcv.iterrows():
            while sig_idx < n_signals:
                signal_time = sig_rows[sig_idx].get("signal_time")
                if signal_time is None or signal_time > ts:
                    break

                signal = sig_rows[sig_idx].copy()
                sig_idx += 1

                signal.setdefault("ticker", ticker)
                signal.setdefault("side", "LONG")
                if "price" not in signal:
                    signal["price"] = float(bar.get("close", 0.0))

                emitted = self._process_strategy_signal(
                    signal, position, {ticker: ohlcv}
                )
                if emitted is not None:
                    out.append(emitted)

            pm_exit = self._maybe_generate_pm_exit(ticker, ts, bar, position)
            if pm_exit is not None:
                out.append(pm_exit)

            pm_entry = self._maybe_generate_pm_entry(ticker, ts, bar, position)
            if pm_entry is not None:
                out.append(pm_entry)

        return out

    def _process_strategy_signal(
        self,
        signal: dict[str, Any],
        position: PositionState,
        ohlcv_by_ticker: dict[str, pd.DataFrame],
    ) -> dict[str, Any] | None:
        side = signal.get("side", "LONG")
        signal_type = signal.get("signal_type", "")
        ctx = PositionRuleContext(signal, position, ohlcv_by_ticker)

        if self._is_entry_signal(side, signal_type):
            if self.pipeline.decide_entry(ctx) and position.size == 0:
                position.size = 1.0
                position.side = side
                price = signal.get("price") or signal.get("close")
                if price is not None:
                    try:
                        position.entry_price = float(price)
                    except (ValueError, TypeError):
                        pass
                return signal
            return None

        if self._is_exit_signal(side, signal_type):
            if position.size <= 0:
                return None

            exit_fraction = self.pipeline.decide_exit(ctx)
            if exit_fraction <= 0.0:
                return None

            position.size = max(0.0, position.size - exit_fraction)
            if position.size <= 0.0:
                position.size = 0.0
                position.side = None
                position.entry_price = None

            if exit_fraction < 1.0:
                signal["fraction"] = exit_fraction

            return signal

        return signal

    def _maybe_generate_pm_exit(
        self,
        ticker: str,
        ts: pd.Timestamp,
        bar: pd.Series,
        position: PositionState,
    ) -> dict[str, Any] | None:
        if position.size <= 0 or position.entry_price is None or position.side is None:
            return None

        current_price = float(bar.get("close", 0.0))
        signal_type = "sell" if position.side == "LONG" else "buy"

        synthetic_signal: dict[str, Any] = {
            "ticker": ticker,
            "signal_time": ts,
            "signal_type": signal_type,
            "side": position.side,
            "price": current_price,
            "pm_generated": True,
        }

        ohlcv_slice = pd.DataFrame([bar])
        ohlcv_slice.index = [ts]
        ctx = PositionRuleContext(synthetic_signal, position, {ticker: ohlcv_slice})

        exit_fraction = self.pipeline.decide_exit(ctx)
        if exit_fraction <= 0.0:
            return None

        position.size = max(0.0, position.size - exit_fraction)
        if position.size <= 0.0:
            position.size = 0.0
            position.side = None
            position.entry_price = None

        if exit_fraction < 1.0:
            synthetic_signal["fraction"] = exit_fraction

        return synthetic_signal

    def _maybe_generate_pm_entry(
        self,
        ticker: str,
        ts: pd.Timestamp,
        bar: pd.Series,
        position: PositionState,
    ) -> dict[str, Any] | None:
        if position.size <= 0 or position.side is None or position.entry_price is None:
            return None

        if not self.pipeline.get_allow_scale_in():
            return None

        current_price = float(bar.get("close", 0.0))
        side = position.side
        signal_type = "buy" if side == "LONG" else "sell"

        synthetic_signal: dict[str, Any] = {
            "ticker": ticker,
            "signal_time": ts,
            "signal_type": signal_type,
            "side": side,
            "price": current_price,
            "pm_generated": True,
            "pm_scale_in": True,
        }

        ohlcv_slice = pd.DataFrame([bar])
        ohlcv_slice.index = [ts]
        ctx = PositionRuleContext(synthetic_signal, position, {ticker: ohlcv_slice})

        allow_entry = self.pipeline.decide_entry(ctx)
        if not allow_entry:
            return None

        position.size += 1.0

        return synthetic_signal


    def apply(
        self,
        signals: pd.DataFrame,
        ohlcv_by_ticker: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        if ohlcv_by_ticker is None:
            ohlcv_by_ticker = {}

        if signals.empty and not ohlcv_by_ticker:
            return signals

        if not signals.empty and ("ticker" not in signals.columns or "signal_type" not in signals.columns):
            self.logger.warning(
                "Signals DataFrame missing required columns (ticker, signal_type). "
                "Returning signals unchanged."
            )
            return signals

        out_rows: list[dict[str, Any]] = []
        position_state: dict[str, PositionState] = {}

        if signals.empty:
            tickers = list(ohlcv_by_ticker.keys())
        else:
            tickers = signals["ticker"].unique().tolist()

        for ticker in tickers:
            if ticker not in position_state:
                position_state[ticker] = PositionState()

            ticker_signals = signals[signals["ticker"] == ticker] if not signals.empty else pd.DataFrame()
            ticker_ohlcv = ohlcv_by_ticker.get(ticker)

            if ticker_ohlcv is not None and not ticker_ohlcv.empty:
                managed_rows = self._apply_for_ticker_with_bars(
                    ticker=ticker,
                    signals_for_ticker=ticker_signals,
                    ohlcv=ticker_ohlcv,
                    position=position_state[ticker],
                )
                out_rows.extend(managed_rows)
            else:
                legacy_rows = self._apply_for_ticker_signals_only(ticker_signals, position_state[ticker])
                out_rows.extend(legacy_rows)

        if not out_rows:
            return pd.DataFrame()

        df = pd.DataFrame(out_rows)
        if "signal_time" in df.columns:
            df = df.sort_values(["ticker", "signal_time"])
        else:
            df = df.sort_values(["ticker"])
        return df
