"""Base classes and protocols for portfolio rules.

This module defines the core data structures and interfaces for portfolio
management rules, including PortfolioState, PortfolioDecision, and PortfolioRule.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from infrastructure.logging.logger import get_logger


@dataclass
class PortfolioPosition:
    """Represents a portfolio position for a single ticker.

    Attributes:
        shares: Number of shares held (can be fractional).
        avg_entry_price: Average entry price per share.
        side: Position side ('LONG' or 'SHORT').
    """

    shares: float = 0.0
    avg_entry_price: float = 0.0
    side: str | None = None


@dataclass
class PortfolioState:
    """Represents the current state of a portfolio.

    Attributes:
        cash_available: Available cash in dollars.
        positions: Dictionary mapping tickers to PortfolioPosition objects.
        pending_settlements: Dictionary mapping settlement dates to cash amounts.
    """

    cash_available: float
    positions: dict[str, PortfolioPosition] = None
    pending_settlements: dict[pd.Timestamp, float] = None

    def __post_init__(self):
        """Initialize default values for optional fields."""
        if self.positions is None:
            self.positions = {}
        if self.pending_settlements is None:
            self.pending_settlements = {}


@dataclass
class PortfolioDecision:
    """Decision result from a portfolio rule evaluation.

    Attributes:
        allow_entry: Whether entry is allowed (None means no decision).
        max_shares: Maximum shares allowed (None means no limit).
        reason: Optional reason for the decision.
    """

    allow_entry: bool | None = None
    max_shares: float | None = None
    reason: str | None = None


class PortfolioRuleContext:
    """Context provided to portfolio rules for evaluation.

    Attributes:
        signal: Signal dictionary containing trade information.
        portfolio_state: Current portfolio state.
        ohlcv_by_ticker: Dictionary mapping tickers to OHLCV dataframes.
    """

    def __init__(
        self,
        signal: dict[str, Any],
        portfolio_state: PortfolioState,
        ohlcv_by_ticker: dict[str, pd.DataFrame],
    ):
        """Initialize PortfolioRuleContext.

        Args:
            signal: Signal dictionary containing trade information.
            portfolio_state: Current portfolio state.
            ohlcv_by_ticker: Dictionary mapping tickers to OHLCV dataframes.
        """
        self.signal = signal
        self.portfolio_state = portfolio_state
        self.ohlcv_by_ticker = ohlcv_by_ticker or {}

    def get_ticker_ohlcv(self, ticker: str) -> pd.DataFrame | None:
        """Get OHLCV data for a ticker.

        Args:
            ticker: Ticker symbol.

        Returns:
            OHLCV dataframe if available, None otherwise.
        """
        return self.ohlcv_by_ticker.get(ticker)


class PortfolioRule(Protocol):
    """Protocol for portfolio rules.

    All portfolio rules must implement the evaluate method.
    """

    def evaluate(self, context: PortfolioRuleContext) -> PortfolioDecision:
        """Evaluate portfolio rule against context.

        Args:
            context: PortfolioRuleContext containing signal and portfolio state.

        Returns:
            PortfolioDecision indicating whether entry is allowed and size limits.
        """
        pass


class PortfolioRulePipeline:
    """Pipeline for applying multiple portfolio rules in sequence."""

    def __init__(self, rules: list[PortfolioRule], logger=None):
        """Initialize PortfolioRulePipeline.

        Args:
            rules: List of PortfolioRule instances to apply.
            logger: Optional logger instance.
        """
        self.rules = rules
        self.logger = logger or get_logger(self.__class__.__name__)

    def decide_entry(self, context: PortfolioRuleContext) -> tuple[bool, float | None, str | None]:
        """Decide whether entry is allowed and maximum shares.

        Args:
            context: PortfolioRuleContext containing signal and portfolio state.

        Returns:
            Tuple of (allow_entry, max_shares, reason).
        """
        allow = True
        max_shares: float | None = None
        chosen_reason: str | None = None

        for rule in self.rules:
            try:
                decision = rule.evaluate(context)
                if decision.allow_entry is False:
                    ticker = context.signal.get("ticker", "unknown")
                    signal_time = context.signal.get("signal_time", "unknown")
                    self.logger.debug(
                        f"Rule {rule.__class__.__name__} rejected entry "
                        f"for {ticker} at {signal_time}: {decision.reason}"
                    )
                    return False, None, decision.reason
                if decision.max_shares is not None:
                    if max_shares is None:
                        max_shares = decision.max_shares
                    else:
                        max_shares = min(max_shares, decision.max_shares)
                    if decision.reason and not chosen_reason:
                        chosen_reason = decision.reason
            except Exception as e:
                ticker = context.signal.get("ticker", "unknown")
                signal_time = context.signal.get("signal_time", "unknown")
                self.logger.warning(
                    f"Rule {rule.__class__.__name__} raised exception "
                    f"for {ticker} at {signal_time}: {e}"
                )
                return False, None, None

        return allow, max_shares, chosen_reason
