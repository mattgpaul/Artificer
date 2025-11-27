"""Unit tests for StopLossRule - Stop Loss Position Exit.

Tests cover initialization, loss threshold evaluation, anchor price calculation,
and error handling. All external dependencies are mocked via conftest.py.
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from system.algo_trader.strategy.position_manager.rules.base import (
    AnchorConfig,
    PositionDecision,
    PositionRuleContext,
    PositionState,
)
from system.algo_trader.strategy.position_manager.rules.stop_loss import StopLossRule


class TestStopLossRuleInitialization:
    """Test StopLossRule initialization."""

    def test_initialization(self, mock_logger):
        """Test StopLossRule initialization."""
        rule = StopLossRule(
            field_price="price",
            loss_pct=0.05,
            fraction=1.0,
            anchor_config=None,
            logger=mock_logger,
        )

        assert rule.field_price == "price"
        assert rule.loss_pct == 0.05
        assert rule.fraction == 1.0
        assert rule.anchor_type == "entry_price"
        assert rule.logger == mock_logger

    def test_initialization_with_anchor_config(self, mock_logger):
        """Test StopLossRule initialization with anchor config."""
        anchor_config = AnchorConfig(
            anchor_type="rolling_min", anchor_field="low", lookback_bars=20, one_shot=True
        )
        rule = StopLossRule(
            field_price="price",
            loss_pct=0.05,
            fraction=1.0,
            anchor_config=anchor_config,
            logger=mock_logger,
        )

        assert rule.anchor_type == "rolling_min"
        assert rule.anchor_field == "low"
        assert rule.lookback_bars == 20
        assert rule.one_shot is True

    def test_from_config_default(self, mock_logger):
        """Test from_config with default parameters."""
        rule = StopLossRule.from_config(
            {"field_price": "price", "loss_pct": 0.05, "fraction": 1.0}, logger=mock_logger
        )

        assert rule is not None
        assert rule.field_price == "price"
        assert rule.loss_pct == 0.05
        assert rule.fraction == 1.0

    def test_from_config_with_anchor(self, mock_logger):
        """Test from_config with anchor configuration."""
        rule = StopLossRule.from_config(
            {
                "field_price": "price",
                "loss_pct": 0.05,
                "fraction": 1.0,
                "anchor": {"type": "rolling_min", "field": "low", "lookback_bars": 20},
            },
            logger=mock_logger,
        )

        assert rule is not None
        assert rule.anchor_type == "rolling_min"
        assert rule.anchor_field == "low"

    def test_from_config_missing_params(self, mock_logger):
        """Test from_config with missing required parameters."""
        rule = StopLossRule.from_config({"field_price": "price"}, logger=mock_logger)

        assert rule is None
        mock_logger.error.assert_called()

    def test_from_config_invalid_params(self, mock_logger):
        """Test from_config with invalid parameters."""
        rule = StopLossRule.from_config(
            {
                "field_price": "price",
                "loss_pct": "invalid",
                "fraction": 1.0,
            },
            logger=mock_logger,
        )

        assert rule is None
        mock_logger.error.assert_called()


class TestStopLossRuleEvaluation:
    """Test StopLossRule evaluation."""

    def test_evaluate_loss_triggered_long(self, mock_logger):
        """Test evaluate with LONG position and loss threshold exceeded."""
        rule = StopLossRule(field_price="price", loss_pct=0.05, fraction=1.0, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 95.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction == 1.0
        assert decision.reason == "stop_loss"

    def test_evaluate_loss_not_triggered_long(self, mock_logger):
        """Test evaluate with LONG position and loss threshold not exceeded."""
        rule = StopLossRule(field_price="price", loss_pct=0.05, fraction=1.0, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 96.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction is None

    def test_evaluate_loss_triggered_short(self, mock_logger):
        """Test evaluate with SHORT position and loss threshold exceeded."""
        rule = StopLossRule(field_price="price", loss_pct=0.05, fraction=1.0, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "buy", "price": 105.0}
        position = PositionState(size=1.0, side="SHORT", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction == 1.0
        assert decision.reason == "stop_loss"

    def test_evaluate_partial_exit(self, mock_logger):
        """Test evaluate with partial exit fraction."""
        rule = StopLossRule(field_price="price", loss_pct=0.05, fraction=0.5, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 95.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction == 0.5

    def test_evaluate_missing_price(self, mock_logger):
        """Test evaluate with missing price."""
        rule = StopLossRule(field_price="price", loss_pct=0.05, fraction=1.0, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell"}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction is None

    def test_evaluate_no_position(self, mock_logger):
        """Test evaluate with no position."""
        rule = StopLossRule(field_price="price", loss_pct=0.05, fraction=1.0, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 95.0}
        position = PositionState(size=0.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction is None

    def test_evaluate_wrong_signal_type(self, mock_logger):
        """Test evaluate with wrong signal type."""
        rule = StopLossRule(field_price="price", loss_pct=0.05, fraction=1.0, logger=mock_logger)

        signal = {"ticker": "AAPL", "signal_type": "buy", "price": 95.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction is None

    def test_evaluate_with_rolling_anchor(self, mock_logger):
        """Test evaluate with rolling anchor price."""
        anchor_config = AnchorConfig(
            anchor_type="rolling_min", anchor_field="low", lookback_bars=5, one_shot=True
        )
        rule = StopLossRule(
            field_price="price",
            loss_pct=0.05,
            fraction=1.0,
            anchor_config=anchor_config,
            logger=mock_logger,
        )

        signal = {
            "ticker": "AAPL",
            "signal_type": "sell",
            "price": 85.0,  # 5% below rolling min of 91.0: (85.0 - 91.0) / 91.0 = -6.6% < -5%
            "signal_time": pd.Timestamp("2024-01-05", tz="UTC"),
        }
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        ohlcv = pd.DataFrame(
            {"low": [95.0, 94.0, 93.0, 92.0, 91.0]},
            index=pd.DatetimeIndex(
                pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
            ),
        )
        context = PositionRuleContext(signal, position, {"AAPL": ohlcv})

        decision = rule.evaluate(context)

        # Should trigger if current price (85.0) is 5% below rolling min (91.0)
        # Loss = (85.0 - 91.0) / 91.0 = -6.0 / 91.0 ≈ -6.6% < -5% threshold
        assert decision.exit_fraction is not None

