"""Fractional position size rule for portfolio management.

This module provides a portfolio rule that sizes positions as a fraction
of total portfolio equity.
"""

import math

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.portfolio_manager.rules.base import (
    PortfolioDecision,
    PortfolioRuleContext,
)


class FractionalPositionSizeRule:
    """Portfolio rule that sizes positions as a fraction of equity.

    Calculates maximum position size based on a fraction of total portfolio equity.
    """

    def __init__(self, fraction_of_equity: float = 0.01, logger=None):
        """Initialize FractionalPositionSizeRule.

        Args:
            fraction_of_equity: Fraction of equity to allocate per position (default 0.01 = 1%).
            logger: Optional logger instance.
        """
        self.fraction_of_equity = fraction_of_equity
        self.logger = logger or get_logger(self.__class__.__name__)

    def _get_mark_price(self, df: pd.DataFrame | None, ts: pd.Timestamp) -> float | None:
        if df is None or df.empty:
            return None
        df_local = df[df.index <= ts]
        if df_local.empty:
            return None
        if "close" in df_local.columns:
            return float(df_local["close"].iloc[-1])
        if "price" in df_local.columns:
            return float(df_local["price"].iloc[-1])
        return None

    def _compute_equity(self, context: PortfolioRuleContext, ts: pd.Timestamp) -> float:
        state = context.portfolio_state
        equity = state.cash_available

        for ticker, pos in state.positions.items():
            if pos.shares <= 0:
                continue
            df = context.get_ticker_ohlcv(ticker)
            mark_price = self._get_mark_price(df, ts)
            if mark_price is None and pos.avg_entry_price > 0:
                mark_price = pos.avg_entry_price
            if mark_price is not None:
                equity += pos.shares * mark_price

        return equity

    def evaluate(self, context: PortfolioRuleContext) -> PortfolioDecision:  # noqa: PLR0911
        """Evaluate fractional position size rule.

        Args:
            context: PortfolioRuleContext containing signal and portfolio state.

        Returns:
            PortfolioDecision with max_shares calculated from equity fraction.
        """
        signal = context.signal
        action = signal.get("action")
        if action not in {"buy_to_open", "sell_to_open"}:
            return PortfolioDecision(allow_entry=True)

        price = signal.get("price")
        signal_time = signal.get("signal_time")
        if price is None or signal_time is None:
            return PortfolioDecision(allow_entry=True)

        try:
            price_f = float(price)
            ts = pd.to_datetime(signal_time, utc=True)
        except (TypeError, ValueError):
            return PortfolioDecision(allow_entry=True)

        equity = self._compute_equity(context, ts)
        if equity <= 0:
            return PortfolioDecision(allow_entry=False, reason="no_equity_for_position")

        target_notional = self.fraction_of_equity * equity
        if target_notional <= 0:
            return PortfolioDecision(allow_entry=False, reason="zero_target_notional")

        raw_shares = target_notional / price_f
        shares = math.floor(raw_shares)
        if shares <= 0:
            return PortfolioDecision(allow_entry=False, reason="zero_target_shares")

        return PortfolioDecision(
            allow_entry=True,
            max_shares=shares,
            reason=f"fractional_size:{self.fraction_of_equity:.2%}",
        )
