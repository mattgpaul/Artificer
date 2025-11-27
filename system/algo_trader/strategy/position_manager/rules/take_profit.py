"""Take profit rule for position management.

This module provides the TakeProfitRule class which triggers position exits
when profits exceed a configured threshold.
"""

from __future__ import annotations

from typing import Any, ClassVar

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.position_manager.rules.base import (
    AnchorConfig,
    PositionDecision,
    PositionRuleContext,
    compute_anchor_price,
    validate_exit_signal_and_get_price,
)


class TakeProfitRule:
    """Rule that triggers position exit when profit target is reached.

    Evaluates current price against anchor price and exits a fraction
    of the position if profit exceeds the configured percentage.
    """

    rule_type: ClassVar[str] = "take_profit"

    def __init__(
        self,
        field_price: str,
        target_pct: float,
        fraction: float,
        anchor_config: AnchorConfig | None = None,
        logger=None,
    ):
        """Initialize take profit rule.

        Args:
            field_price: Field name in signal containing current price.
            target_pct: Profit percentage target (e.g., 0.10 for 10%).
            fraction: Fraction of position to exit when triggered (0.0 to 1.0).
            anchor_config: Configuration for anchor price calculation. If None, uses defaults.
            logger: Optional logger instance.
        """
        self.field_price = field_price
        self.target_pct = target_pct
        self.fraction = fraction
        if anchor_config is None:
            anchor_config = AnchorConfig()
        self.anchor_type = anchor_config.anchor_type or "entry_price"
        self.anchor_field = anchor_config.anchor_field or field_price
        self.lookback_bars = anchor_config.lookback_bars
        self.one_shot = anchor_config.one_shot
        self.logger = logger or get_logger(self.__class__.__name__)

    def evaluate(self, context: PositionRuleContext) -> PositionDecision:
        """Evaluate take profit rule and return exit decision if triggered.

        Args:
            context: Rule evaluation context.

        Returns:
            PositionDecision with exit_fraction if profit target reached.
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

        if pnl_pct >= self.target_pct:
            return PositionDecision(exit_fraction=self.fraction, reason="take_profit")
        return PositionDecision()

    @classmethod
    def from_config(cls, params: dict[str, Any], logger=None) -> "TakeProfitRule" | None:
        field_price = params.get("field_price")
        target_pct = params.get("target_pct")
        fraction = params.get("fraction")
        if field_price is None or target_pct is None or fraction is None:
            if logger is not None:
                logger.error(
                    "take_profit rule missing required params: field_price, target_pct, fraction"
                )
            return None
        anchor_cfg = params.get("anchor", {}) or {}
        anchor_config = AnchorConfig(
            anchor_type=anchor_cfg.get("type", "entry_price"),
            anchor_field=anchor_cfg.get("field"),
            lookback_bars=int(anchor_cfg["lookback_bars"])
            if anchor_cfg.get("lookback_bars") is not None
            else None,
            one_shot=bool(params.get("one_shot", True)),
        )
        try:
            return cls(
                field_price=field_price,
                target_pct=float(target_pct),
                fraction=float(fraction),
                anchor_config=anchor_config,
                logger=logger,
            )
        except (ValueError, TypeError) as e:
            if logger is not None:
                logger.error(
                    f"take_profit rule params must be numeric where required: {e}"
                )
            return None
