"""Unit tests for ScalingRule - Position Scaling Control.

Tests cover initialization, scale-in/scale-out control, and error handling.
All external dependencies are mocked via conftest.py.
"""

from system.algo_trader.strategy.position_manager.rules.base import (
    PositionRuleContext,
    PositionState,
)
from system.algo_trader.strategy.position_manager.rules.scaling import ScalingRule


class TestScalingRuleInitialization:
    """Test ScalingRule initialization."""

    def test_initialization(self, mock_logger):
        """Test ScalingRule initialization."""
        rule = ScalingRule(allow_scale_in=True, allow_scale_out=False, logger=mock_logger)

        assert rule.allow_scale_in is True
        assert rule.allow_scale_out is False
        assert rule.logger == mock_logger

    def test_from_config_default(self, mock_logger):
        """Test from_config with default parameters."""
        rule = ScalingRule.from_config({}, logger=mock_logger)

        assert rule is not None
        assert rule.allow_scale_in is False
        assert rule.allow_scale_out is True

    def test_from_config_custom(self, mock_logger):
        """Test from_config with custom parameters."""
        rule = ScalingRule.from_config(
            {"allow_scale_in": True, "allow_scale_out": False}, logger=mock_logger
        )

        assert rule is not None
        assert rule.allow_scale_in is True
        assert rule.allow_scale_out is False


class TestScalingRuleEvaluation:
    """Test ScalingRule evaluation."""

    def test_evaluate_entry_no_position(self, mock_logger):
        """Test evaluate with entry signal and no existing position."""
        rule = ScalingRule(allow_scale_in=False, allow_scale_out=True, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "buy", "side": "LONG"}
        position = PositionState(size=0.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is None  # No opinion

    def test_evaluate_entry_with_position_scale_in_allowed(self, mock_logger):
        """Test evaluate with entry signal, existing position, scale-in allowed."""
        rule = ScalingRule(allow_scale_in=True, allow_scale_out=True, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "buy", "side": "LONG"}
        position = PositionState(size=1.0, side="LONG")
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is None  # No opinion

    def test_evaluate_entry_with_position_scale_in_disallowed(self, mock_logger):
        """Test evaluate with entry signal, existing position, scale-in disallowed."""
        rule = ScalingRule(allow_scale_in=False, allow_scale_out=True, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "buy", "side": "LONG"}
        position = PositionState(size=1.0, side="LONG")
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is False

    def test_evaluate_exit_signal(self, mock_logger):
        """Test evaluate with exit signal."""
        rule = ScalingRule(allow_scale_in=False, allow_scale_out=True, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "side": "LONG"}
        position = PositionState(size=1.0, side="LONG")
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is None  # No opinion for exit signals

    def test_evaluate_short_entry(self, mock_logger):
        """Test evaluate with SHORT entry signal."""
        rule = ScalingRule(allow_scale_in=False, allow_scale_out=True, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "side": "SHORT"}
        position = PositionState(size=1.0, side="SHORT")
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is False

    def test_evaluate_short_exit(self, mock_logger):
        """Test evaluate with SHORT exit signal."""
        rule = ScalingRule(allow_scale_in=False, allow_scale_out=True, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "buy", "side": "SHORT"}
        position = PositionState(size=1.0, side="SHORT")
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is None  # No opinion for exit signals
