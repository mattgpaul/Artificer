"""Stop loss rule for position management.

This module provides the StopLossRule class which triggers position exits
when losses exceed a configured threshold.
"""

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.position_manager.rules.base import (
    AnchorConfig,
    PositionDecision,
    PositionRuleContext,
    compute_anchor_price,
    validate_exit_signal_and_get_price,
)


class StopLossRule:
    """Rule that triggers position exit when loss threshold is exceeded.

    Evaluates current price against anchor price and exits a fraction
    of the position if loss exceeds the configured percentage.
    """

    def __init__(
        self,
        field_price: str,
        loss_pct: float,
        fraction: float,
        anchor_config: AnchorConfig | None = None,
        logger=None,
    ):
        """Initialize stop loss rule.

        Args:
            field_price: Field name in signal containing current price.
            loss_pct: Loss percentage threshold (e.g., 0.05 for 5%).
            fraction: Fraction of position to exit when triggered (0.0 to 1.0).
            anchor_config: Configuration for anchor price calculation. If None, uses defaults.
            logger: Optional logger instance.
        """
        self.field_price = field_price
        self.loss_pct = loss_pct
        self.fraction = fraction
        if anchor_config is None:
            anchor_config = AnchorConfig()
        self.anchor_type = anchor_config.anchor_type or "entry_price"
        self.anchor_field = anchor_config.anchor_field or field_price
        self.lookback_bars = anchor_config.lookback_bars
        self.one_shot = anchor_config.one_shot
        self.logger = logger or get_logger(self.__class__.__name__)

    def evaluate(self, context: PositionRuleContext) -> PositionDecision:
        """Evaluate stop loss rule and return exit decision if triggered.

        Args:
            context: Rule evaluation context.

        Returns:
            PositionDecision with exit_fraction if loss threshold exceeded.
        """
        current = validate_exit_signal_and_get_price(context, self.field_price)
        if current is None:
            return PositionDecision()

        anchor_price = compute_anchor_price(
            context,
            self.anchor_type,
            self.anchor_field,
            self.lookback_bars,
        )
        if anchor_price is None or anchor_price <= 0.0:
            return PositionDecision()

        pnl_pct = (current - anchor_price) / anchor_price
        if context.position.side == "SHORT":
            pnl_pct *= -1

        if pnl_pct <= -self.loss_pct:
            return PositionDecision(exit_fraction=self.fraction, reason="stop_loss")
        return PositionDecision()
