"""Position rule pipeline for evaluating multiple rules in sequence.

This module provides the PositionRulePipeline class which evaluates a list
of position rules and combines their decisions.
"""

from __future__ import annotations

from infrastructure.logging.logger import get_logger
from system.algo_trader.domain.strategy.position_manager.rules.base import (
    PositionRule,
    PositionRuleContext,
)
from system.algo_trader.domain.strategy.position_manager.rules.scaling import ScalingRule


class PositionRulePipeline:
    """Pipeline for evaluating multiple position rules in sequence.

    The pipeline evaluates rules for entry and exit decisions, tracking
    one-shot rule state per ticker.
    """

    def __init__(self, rules: list[PositionRule], logger=None):
        """Initialize rule pipeline.

        Args:
            rules: List of position rules to evaluate.
            logger: Optional logger instance.
        """
        self.rules = rules
        self.logger = logger or get_logger(self.__class__.__name__)
        # Tracks which one-shot rules have already fired per ticker for the
        # current open position lifecycle. Keyed by ticker -> set(rule_index).
        self._fired_rules: dict[str, set[int]] = {}

    def decide_entry(self, context: PositionRuleContext) -> bool:
        """Decide whether entry is allowed based on all rules.

        Args:
            context: Rule evaluation context.

        Returns:
            True if all rules allow entry, False otherwise.
        """
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
        """Get whether scale-out is allowed from scaling rule.

        Returns:
            True if scale-out is allowed, False otherwise.
        """
        for rule in self.rules:
            if isinstance(rule, ScalingRule):
                return rule.allow_scale_out
        return True

    def get_allow_scale_in(self) -> bool:
        """Get whether scale-in is allowed from scaling rule.

        Returns:
            True if scale-in is allowed, False otherwise.
        """
        for rule in self.rules:
            if isinstance(rule, ScalingRule):
                return rule.allow_scale_in
        return False

    def reset_for_ticker(self, ticker: str) -> None:
        """Reset one-shot rule state for a ticker when its position goes flat."""
        if ticker in self._fired_rules:
            del self._fired_rules[ticker]

    def decide_exit(self, context: PositionRuleContext) -> tuple[float, str | None]:
        """Decide exit fraction based on all rules.

        Args:
            context: Rule evaluation context.

        Returns:
            Tuple of (exit_fraction, reason) where exit_fraction is 0.0 to 1.0.
        """
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
