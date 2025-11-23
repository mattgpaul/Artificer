"""Scaling rule for position management.

This module provides the ScalingRule class which controls whether positions
can be scaled in (added to) or scaled out (partially closed).
"""

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.position_manager.rules.base import (
    PositionDecision,
    PositionRuleContext,
)


class ScalingRule:
    """Rule that controls position scaling behavior.

    Prevents scale-in (adding to existing positions) if not allowed.
    """

    def __init__(self, allow_scale_in: bool, allow_scale_out: bool, logger=None):
        """Initialize scaling rule.

        Args:
            allow_scale_in: Whether to allow adding to existing positions.
            allow_scale_out: Whether to allow partial position exits.
            logger: Optional logger instance.
        """
        self.allow_scale_in = allow_scale_in
        self.allow_scale_out = allow_scale_out
        self.logger = logger or get_logger(self.__class__.__name__)

    def evaluate(self, context: PositionRuleContext) -> PositionDecision:
        """Evaluate scaling rule for entry signals.

        Args:
            context: Rule evaluation context.

        Returns:
            PositionDecision blocking entry if scale-in not allowed and position exists.
        """
        signal_type = context.signal.get("signal_type", "")
        side = context.signal.get("side", "LONG")
        is_entry = (side == "LONG" and signal_type == "buy") or (
            side == "SHORT" and signal_type == "sell"
        )

        if is_entry and context.position.size > 0 and not self.allow_scale_in:
            return PositionDecision(allow_entry=False)
        return PositionDecision()
