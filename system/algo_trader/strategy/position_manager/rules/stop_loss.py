from infrastructure.logging.logger import get_logger

from system.algo_trader.strategy.position_manager.rules.base import (
    PositionDecision,
    PositionRuleContext,
    compute_anchor_price,
    validate_exit_signal_and_get_price,
)


class StopLossRule:
    def __init__(
        self,
        field_price: str,
        loss_pct: float,
        fraction: float,
        anchor_type: str = "entry_price",
        anchor_field: str | None = None,
        lookback_bars: int | None = None,
        one_shot: bool = True,
        logger=None,
    ):
        self.field_price = field_price
        self.loss_pct = loss_pct
        self.fraction = fraction
        self.anchor_type = anchor_type or "entry_price"
        self.anchor_field = anchor_field or field_price
        self.lookback_bars = lookback_bars
        self.one_shot = one_shot
        self.logger = logger or get_logger(self.__class__.__name__)

    def evaluate(self, context: PositionRuleContext) -> PositionDecision:
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

