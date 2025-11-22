from infrastructure.logging.logger import get_logger

from system.algo_trader.strategy.position_manager.rules.base import (
    PositionDecision,
    PositionRuleContext,
    validate_exit_signal_and_get_price,
)


class StopLossRule:
    def __init__(self, field_price: str, loss_pct: float, fraction: float, logger=None):
        self.field_price = field_price
        self.loss_pct = loss_pct
        self.fraction = fraction
        self.logger = logger or get_logger(self.__class__.__name__)

    def evaluate(self, context: PositionRuleContext) -> PositionDecision:
        current = validate_exit_signal_and_get_price(context, self.field_price)
        if current is None:
            return PositionDecision()

        pnl_pct = (current - context.position.entry_price) / context.position.entry_price
        if context.position.side == "SHORT":
            pnl_pct *= -1

        if pnl_pct <= -self.loss_pct:
            return PositionDecision(exit_fraction=self.fraction)
        return PositionDecision()

