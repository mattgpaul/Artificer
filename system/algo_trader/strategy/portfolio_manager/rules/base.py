from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from infrastructure.logging.logger import get_logger


@dataclass
class PortfolioPosition:
    shares: float = 0.0
    avg_entry_price: float = 0.0
    side: str | None = None


@dataclass
class PortfolioState:
    cash_available: float
    positions: dict[str, PortfolioPosition] = None
    pending_settlements: dict[pd.Timestamp, float] = None

    def __post_init__(self):
        if self.positions is None:
            self.positions = {}
        if self.pending_settlements is None:
            self.pending_settlements = {}


@dataclass
class PortfolioDecision:
    allow_entry: bool | None = None
    max_shares: float | None = None
    reason: str | None = None


class PortfolioRuleContext:
    def __init__(
        self,
        signal: dict[str, Any],
        portfolio_state: PortfolioState,
        ohlcv_by_ticker: dict[str, pd.DataFrame],
    ):
        self.signal = signal
        self.portfolio_state = portfolio_state
        self.ohlcv_by_ticker = ohlcv_by_ticker or {}

    def get_ticker_ohlcv(self, ticker: str) -> pd.DataFrame | None:
        return self.ohlcv_by_ticker.get(ticker)


class PortfolioRule(Protocol):
    def evaluate(self, context: PortfolioRuleContext) -> PortfolioDecision:
        pass


class PortfolioRulePipeline:
    def __init__(self, rules: list[PortfolioRule], logger=None):
        self.rules = rules
        self.logger = logger or get_logger(self.__class__.__name__)

    def decide_entry(
        self, context: PortfolioRuleContext
    ) -> tuple[bool, float | None, str | None]:
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

