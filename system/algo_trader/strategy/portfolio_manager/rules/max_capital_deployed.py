"""Maximum capital deployed rule for portfolio management.

This module provides a portfolio rule that limits the percentage of
total capital that can be deployed in positions.
"""

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.portfolio_manager.rules.base import (
    PortfolioDecision,
    PortfolioRuleContext,
)


class MaxCapitalDeployedRule:
    """Portfolio rule that limits maximum capital deployment percentage.

    Blocks new entries when deployed capital exceeds the configured percentage.
    """

    def __init__(self, max_deployed_pct: float = 0.5, logger=None):
        """Initialize MaxCapitalDeployedRule.

        Args:
            max_deployed_pct: Maximum percentage of capital that can be deployed
                (default 0.5 = 50%).
            logger: Optional logger instance.
        """
        self.max_deployed_pct = max_deployed_pct
        self.logger = logger or get_logger(self.__class__.__name__)

    def evaluate(self, context: PortfolioRuleContext) -> PortfolioDecision:
        """Evaluate maximum capital deployed rule.

        Args:
            context: PortfolioRuleContext containing signal and portfolio state.

        Returns:
            PortfolioDecision blocking entry if deployment limit exceeded.
        """
        signal = context.signal
        action = signal.get("action")
        entry_actions = {"buy_to_open", "sell_to_open"}
        if action not in entry_actions:
            return PortfolioDecision(allow_entry=True)

        price = signal.get("price")
        shares = signal.get("shares")
        if price is None or shares is None:
            return PortfolioDecision(allow_entry=True)

        try:
            float(price)
            float(shares)
        except (TypeError, ValueError):
            return PortfolioDecision(allow_entry=True)

        state = context.portfolio_state
        total_deployed = 0.0
        for pos in state.positions.values():
            if pos.shares > 0 and pos.avg_entry_price > 0:
                total_deployed += pos.shares * pos.avg_entry_price

        realized_capital = state.cash_available + total_deployed
        if realized_capital <= 0:
            return PortfolioDecision(allow_entry=True)

        deployed_pct = total_deployed / realized_capital
        if deployed_pct >= self.max_deployed_pct:
            ticker = signal.get("ticker", "unknown")
            self.logger.debug(
                f"MaxCapitalDeployedRule: blocking entry for {ticker} - "
                f"deployed {deployed_pct:.2%} >= {self.max_deployed_pct:.2%}"
            )
            return PortfolioDecision(
                allow_entry=False,
                reason=f"capital_deployed_limit: {deployed_pct:.2%} >= {self.max_deployed_pct:.2%}",
            )

        return PortfolioDecision(allow_entry=True)
