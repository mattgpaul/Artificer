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
        # Tracks which one-shot rules have already fired per ticker for the
        # current open position lifecycle. Keyed by ticker -> set(rule_index).
        self._fired_rules: dict[str, set[int]] = {}

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

    def reset_for_ticker(self, ticker: str) -> None:
        """Reset one-shot rule state for a ticker when its position goes flat."""
        if ticker in self._fired_rules:
            del self._fired_rules[ticker]

    def decide_exit(self, context: PositionRuleContext) -> tuple[float, str | None]:
        allow_scale_out = self.get_allow_scale_out()
        max_fraction = 0.0
        chosen_reason: str | None = None

        ticker = context.signal.get("ticker", "unknown")
        fired_for_ticker = self._fired_rules.setdefault(ticker, set())

        for idx, rule in enumerate(self.rules):
            try:
                is_one_shot = bool(getattr(rule, "one_shot", False))
                if is_one_shot and idx in fired_for_ticker:
                    continue

                decision = rule.evaluate(context)
                if decision.exit_fraction is not None and decision.exit_fraction > 0.0:
                    if decision.exit_fraction > max_fraction:
                        max_fraction = decision.exit_fraction
                        chosen_reason = decision.reason
                    if is_one_shot:
                        fired_for_ticker.add(idx)
            except Exception as e:
                signal_time = context.signal.get("signal_time", "unknown")
                self.logger.warning(
                    f"Rule {rule.__class__.__name__} raised exception "
                    f"for {ticker} at {signal_time}: {e}"
                )

        if not allow_scale_out and max_fraction > 0.0:
            return 1.0, chosen_reason
        fraction = max(0.0, min(1.0, max_fraction))
        return fraction, chosen_reason

