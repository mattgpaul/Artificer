"""Unit tests for PositionRulePipeline - Position Rule Pipeline.

Tests cover initialization, entry decisions, exit decisions, one-shot rule tracking,
and scaling rule integration. All external dependencies are mocked via conftest.py.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.strategy.position_manager.rules.base import (
    PositionDecision,
    PositionRuleContext,
    PositionState,
)
from system.algo_trader.strategy.position_manager.rules.pipeline import PositionRulePipeline
from system.algo_trader.strategy.position_manager.rules.scaling import ScalingRule


class TestPositionRulePipelineInitialization:
    """Test PositionRulePipeline initialization."""

    def test_initialization(self, mock_logger):
        """Test PositionRulePipeline initialization."""
        rules = []
        pipeline = PositionRulePipeline(rules, logger=mock_logger)

        assert pipeline.rules == rules
        assert pipeline.logger == mock_logger
        assert pipeline._fired_rules == {}

    def test_initialization_creates_logger(self):
        """Test initialization creates logger if not provided."""
        rules = []
        with patch("system.algo_trader.strategy.position_manager.rules.pipeline.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            pipeline = PositionRulePipeline(rules)

            assert pipeline.logger == mock_logger


class TestPositionRulePipelineEntry:
    """Test PositionRulePipeline entry decisions."""

    def test_decide_entry_all_allow(self, mock_logger):
        """Test decide_entry when all rules allow entry."""
        rule1 = MagicMock()
        rule1.evaluate.return_value = PositionDecision(allow_entry=True)
        rule2 = MagicMock()
        rule2.evaluate.return_value = PositionDecision(allow_entry=True)

        pipeline = PositionRulePipeline([rule1, rule2], logger=mock_logger)

        signal = {"ticker": "AAPL"}
        position = PositionState()
        context = PositionRuleContext(signal, position, {})

        result = pipeline.decide_entry(context)

        assert result is True

    def test_decide_entry_one_rejects(self, mock_logger):
        """Test decide_entry when one rule rejects entry."""
        rule1 = MagicMock()
        rule1.evaluate.return_value = PositionDecision(allow_entry=True)
        rule2 = MagicMock()
        rule2.evaluate.return_value = PositionDecision(allow_entry=False)

        pipeline = PositionRulePipeline([rule1, rule2], logger=mock_logger)

        signal = {"ticker": "AAPL"}
        position = PositionState()
        context = PositionRuleContext(signal, position, {})

        result = pipeline.decide_entry(context)

        assert result is False
        mock_logger.debug.assert_called()

    def test_decide_entry_exception_handling(self, mock_logger):
        """Test decide_entry handles exceptions from rules."""
        rule1 = MagicMock()
        rule1.evaluate.side_effect = Exception("Test error")

        pipeline = PositionRulePipeline([rule1], logger=mock_logger)

        signal = {"ticker": "AAPL"}
        position = PositionState()
        context = PositionRuleContext(signal, position, {})

        result = pipeline.decide_entry(context)

        assert result is False
        mock_logger.warning.assert_called()


class TestPositionRulePipelineExit:
    """Test PositionRulePipeline exit decisions."""

    def test_decide_exit_no_exits(self, mock_logger):
        """Test decide_exit when no rules trigger exit."""
        rule1 = MagicMock()
        rule1.evaluate.return_value = PositionDecision()

        pipeline = PositionRulePipeline([rule1], logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 150.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        fraction, reason = pipeline.decide_exit(context)

        assert fraction == 0.0
        assert reason is None

    def test_decide_exit_one_rule_triggers(self, mock_logger):
        """Test decide_exit when one rule triggers exit."""
        rule1 = MagicMock()
        rule1.evaluate.return_value = PositionDecision(exit_fraction=0.5, reason="take_profit")

        pipeline = PositionRulePipeline([rule1], logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 150.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        fraction, reason = pipeline.decide_exit(context)

        assert fraction == 0.5
        assert reason == "take_profit"

    def test_decide_exit_multiple_rules_max_fraction(self, mock_logger):
        """Test decide_exit takes maximum fraction from multiple rules."""
        rule1 = MagicMock()
        rule1.evaluate.return_value = PositionDecision(exit_fraction=0.3, reason="take_profit")
        rule2 = MagicMock()
        rule2.evaluate.return_value = PositionDecision(exit_fraction=0.7, reason="stop_loss")

        pipeline = PositionRulePipeline([rule1, rule2], logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 150.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        fraction, reason = pipeline.decide_exit(context)

        assert fraction == 0.7
        assert reason == "stop_loss"

    def test_decide_exit_one_shot_rule(self, mock_logger):
        """Test decide_exit with one-shot rule."""
        rule1 = MagicMock()
        rule1.one_shot = True
        rule1.evaluate.return_value = PositionDecision(exit_fraction=0.5, reason="take_profit")

        pipeline = PositionRulePipeline([rule1], logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 150.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        # First call should trigger
        fraction1, reason1 = pipeline.decide_exit(context)
        assert fraction1 == 0.5

        # Second call should not trigger (one-shot)
        fraction2, reason2 = pipeline.decide_exit(context)
        assert fraction2 == 0.0

    def test_decide_exit_scale_out_disabled(self, mock_logger):
        """Test decide_exit when scale-out is disabled."""
        scaling = ScalingRule(allow_scale_in=False, allow_scale_out=False)
        rule1 = MagicMock()
        rule1.evaluate.return_value = PositionDecision(exit_fraction=0.5, reason="take_profit")

        pipeline = PositionRulePipeline([scaling, rule1], logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 150.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        fraction, reason = pipeline.decide_exit(context)

        # Should return 1.0 (full exit) when scale-out is disabled
        assert fraction == 1.0

    def test_decide_exit_exception_handling(self, mock_logger):
        """Test decide_exit handles exceptions from rules."""
        rule1 = MagicMock()
        rule1.evaluate.side_effect = Exception("Test error")

        pipeline = PositionRulePipeline([rule1], logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 150.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        fraction, reason = pipeline.decide_exit(context)

        assert fraction == 0.0
        mock_logger.warning.assert_called()


class TestPositionRulePipelineScaling:
    """Test PositionRulePipeline scaling rule integration."""

    def test_get_allow_scale_out_with_scaling_rule(self, mock_logger):
        """Test get_allow_scale_out with ScalingRule."""
        scaling = ScalingRule(allow_scale_in=False, allow_scale_out=True)
        pipeline = PositionRulePipeline([scaling], logger=mock_logger)

        assert pipeline.get_allow_scale_out() is True

    def test_get_allow_scale_out_without_scaling_rule(self, mock_logger):
        """Test get_allow_scale_out without ScalingRule."""
        rule1 = MagicMock()
        pipeline = PositionRulePipeline([rule1], logger=mock_logger)

        assert pipeline.get_allow_scale_out() is True  # Default

    def test_get_allow_scale_in_with_scaling_rule(self, mock_logger):
        """Test get_allow_scale_in with ScalingRule."""
        scaling = ScalingRule(allow_scale_in=True, allow_scale_out=True)
        pipeline = PositionRulePipeline([scaling], logger=mock_logger)

        assert pipeline.get_allow_scale_in() is True

    def test_get_allow_scale_in_without_scaling_rule(self, mock_logger):
        """Test get_allow_scale_in without ScalingRule."""
        rule1 = MagicMock()
        pipeline = PositionRulePipeline([rule1], logger=mock_logger)

        assert pipeline.get_allow_scale_in() is False  # Default


class TestPositionRulePipelineReset:
    """Test PositionRulePipeline reset functionality."""

    def test_reset_for_ticker(self, mock_logger):
        """Test reset_for_ticker clears one-shot rule state."""
        rule1 = MagicMock()
        rule1.one_shot = True
        rule1.evaluate.return_value = PositionDecision(exit_fraction=0.5, reason="take_profit")

        pipeline = PositionRulePipeline([rule1], logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 150.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        # Trigger one-shot rule
        pipeline.decide_exit(context)

        # Reset for ticker
        pipeline.reset_for_ticker("AAPL")

        # Rule should be able to fire again
        fraction, reason = pipeline.decide_exit(context)
        assert fraction == 0.5

