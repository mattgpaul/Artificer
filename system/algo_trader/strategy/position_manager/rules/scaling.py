from infrastructure.logging.logger import get_logger

from system.algo_trader.strategy.position_manager.rules.base import (
    PositionDecision,
    PositionRuleContext,
)


class ScalingRule:
    def __init__(self, allow_scale_in: bool, allow_scale_out: bool, logger=None):
        self.allow_scale_in = allow_scale_in
        self.allow_scale_out = allow_scale_out
        self.logger = logger or get_logger(self.__class__.__name__)

    def evaluate(self, context: PositionRuleContext) -> PositionDecision:
        signal_type = context.signal.get("signal_type", "")
        side = context.signal.get("side", "LONG")
        is_entry = (side == "LONG" and signal_type == "buy") or (
            side == "SHORT" and signal_type == "sell"
        )
        is_exit = (side == "LONG" and signal_type == "sell") or (
            side == "SHORT" and signal_type == "buy"
        )

        if is_entry and context.position.size > 0 and not self.allow_scale_in:
            return PositionDecision(allow_entry=False)
        return PositionDecision()

