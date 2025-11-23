from infrastructure.logging.logger import get_logger

from system.algo_trader.strategy.position_manager.rules.base import (
    PositionRule,
    PositionRuleContext,
)
from system.algo_trader.strategy.position_manager.rules.scaling import ScalingRule


class PositionRulePipeline:
    def __init__(self, rules: list[PositionRule], logger=None):
        self.rules = rules
        self.logger = logger or get_logger(self.__class__.__name__)

    def decide_entry(self, context: PositionRuleContext) -> bool:
        for rule in self.rules:
            try:
                decision = rule.evaluate(context)
                if decision.allow_entry is False:
                    ticker = context.signal.get("ticker", "unknown")
                    signal_time = context.signal.get("signal_time", "unknown")
                    self.logger.debug(
                        f"Rule {rule.__class__.__name__} rejected entry "
                        f"for {ticker} at {signal_time}"
                    )
                    return False
            except Exception as e:
                ticker = context.signal.get("ticker", "unknown")
                signal_time = context.signal.get("signal_time", "unknown")
                self.logger.warning(
                    f"Rule {rule.__class__.__name__} raised exception "
                    f"for {ticker} at {signal_time}: {e}"
                )
                return False
        return True

    def get_allow_scale_out(self) -> bool:
        for rule in self.rules:
            if isinstance(rule, ScalingRule):
                return rule.allow_scale_out
        return True

    def get_allow_scale_in(self) -> bool:
        for rule in self.rules:
            if isinstance(rule, ScalingRule):
                return rule.allow_scale_in
        return False

    def decide_exit(self, context: PositionRuleContext) -> float:
        allow_scale_out = self.get_allow_scale_out()
        max_fraction = 0.0
        for rule in self.rules:
            try:
                decision = rule.evaluate(context)
                if decision.exit_fraction is not None:
                    max_fraction = max(max_fraction, decision.exit_fraction)
            except Exception as e:
                ticker = context.signal.get("ticker", "unknown")
                signal_time = context.signal.get("signal_time", "unknown")
                self.logger.warning(
                    f"Rule {rule.__class__.__name__} raised exception "
                    f"for {ticker} at {signal_time}: {e}"
                )
        if not allow_scale_out and max_fraction > 0.0:
            return 1.0
        return max(0.0, min(1.0, max_fraction))

