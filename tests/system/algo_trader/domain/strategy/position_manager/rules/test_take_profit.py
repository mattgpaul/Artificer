"""Unit tests for TakeProfitRule - Take Profit Position Exit.

Tests cover initialization, profit target evaluation, anchor price calculation,
and error handling. All external dependencies are mocked via conftest.py.
"""

import pandas as pd

from system.algo_trader.strategy.position_manager.rules.base import (
    AnchorConfig,
    PositionRuleContext,
    PositionState,
)
from system.algo_trader.strategy.position_manager.rules.take_profit import TakeProfitRule


class TestTakeProfitRuleInitialization:
    """Test TakeProfitRule initialization."""

    def test_initialization(self, mock_logger):
        """Test TakeProfitRule initialization."""
        rule = TakeProfitRule(
            field_price="price",
            target_pct=0.10,
            fraction=0.5,
            anchor_config=None,
            logger=mock_logger,
        )

        assert rule.field_price == "price"
        assert rule.target_pct == 0.10
        assert rule.fraction == 0.5
        assert rule.anchor_type == "entry_price"
        assert rule.logger == mock_logger

    def test_initialization_with_anchor_config(self, mock_logger):
        """Test TakeProfitRule initialization with anchor config."""
        anchor_config = AnchorConfig(
            anchor_type="rolling_max", anchor_field="high", lookback_bars=20, one_shot=True
        )
        rule = TakeProfitRule(
            field_price="price",
            target_pct=0.10,
            fraction=0.5,
            anchor_config=anchor_config,
            logger=mock_logger,
        )

        assert rule.anchor_type == "rolling_max"
        assert rule.anchor_field == "high"
        assert rule.lookback_bars == 20
        assert rule.one_shot is True

    def test_from_config_default(self, mock_logger):
        """Test from_config with default parameters."""
        rule = TakeProfitRule.from_config(
            {"field_price": "price", "target_pct": 0.10, "fraction": 0.5}, logger=mock_logger
        )

        assert rule is not None
        assert rule.field_price == "price"
        assert rule.target_pct == 0.10
        assert rule.fraction == 0.5

    def test_from_config_with_anchor(self, mock_logger):
        """Test from_config with anchor configuration."""
        rule = TakeProfitRule.from_config(
            {
                "field_price": "price",
                "target_pct": 0.10,
                "fraction": 0.5,
                "anchor": {"type": "rolling_max", "field": "high", "lookback_bars": 20},
            },
            logger=mock_logger,
        )

        assert rule is not None
        assert rule.anchor_type == "rolling_max"
        assert rule.anchor_field == "high"

    def test_from_config_missing_params(self, mock_logger):
        """Test from_config with missing required parameters."""
        rule = TakeProfitRule.from_config({"field_price": "price"}, logger=mock_logger)

        assert rule is None
        mock_logger.error.assert_called()

    def test_from_config_invalid_params(self, mock_logger):
        """Test from_config with invalid parameters."""
        rule = TakeProfitRule.from_config(
            {
                "field_price": "price",
                "target_pct": "invalid",
                "fraction": 0.5,
            },
            logger=mock_logger,
        )

        assert rule is None
        mock_logger.error.assert_called()


class TestTakeProfitRuleEvaluation:
    """Test TakeProfitRule evaluation."""

    def test_evaluate_profit_triggered_long(self, mock_logger):
        """Test evaluate with LONG position and profit target reached."""
        rule = TakeProfitRule(
            field_price="price", target_pct=0.10, fraction=0.5, logger=mock_logger
        )

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 110.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction == 0.5
        assert decision.reason == "take_profit"

    def test_evaluate_profit_not_triggered_long(self, mock_logger):
        """Test evaluate with LONG position and profit target not reached."""
        rule = TakeProfitRule(
            field_price="price", target_pct=0.10, fraction=0.5, logger=mock_logger
        )

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 109.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction is None

    def test_evaluate_profit_triggered_short(self, mock_logger):
        """Test evaluate with SHORT position and profit target reached."""
        rule = TakeProfitRule(
            field_price="price", target_pct=0.10, fraction=0.5, logger=mock_logger
        )

        signal = {"ticker": "AAPL", "signal_type": "buy", "price": 90.0}
        position = PositionState(size=1.0, side="SHORT", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction == 0.5
        assert decision.reason == "take_profit"

    def test_evaluate_full_exit(self, mock_logger):
        """Test evaluate with full exit fraction."""
        rule = TakeProfitRule(
            field_price="price", target_pct=0.10, fraction=1.0, logger=mock_logger
        )

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 110.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction == 1.0

    def test_evaluate_missing_price(self, mock_logger):
        """Test evaluate with missing price."""
        rule = TakeProfitRule(
            field_price="price", target_pct=0.10, fraction=0.5, logger=mock_logger
        )

        signal = {"ticker": "AAPL", "signal_type": "sell"}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction is None

    def test_evaluate_no_position(self, mock_logger):
        """Test evaluate with no position."""
        rule = TakeProfitRule(
            field_price="price", target_pct=0.10, fraction=0.5, logger=mock_logger
        )

        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 110.0}
        position = PositionState(size=0.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction is None

    def test_evaluate_wrong_signal_type(self, mock_logger):
        """Test evaluate with wrong signal type."""
        rule = TakeProfitRule(
            field_price="price", target_pct=0.10, fraction=0.5, logger=mock_logger
        )

        signal = {"ticker": "AAPL", "signal_type": "buy", "price": 110.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        decision = rule.evaluate(context)

        assert decision.exit_fraction is None

    def test_evaluate_with_rolling_anchor(self, mock_logger):
        """Test evaluate with rolling anchor price."""
        anchor_config = AnchorConfig(
            anchor_type="rolling_max", anchor_field="high", lookback_bars=5, one_shot=True
        )
        rule = TakeProfitRule(
            field_price="price",
            target_pct=0.10,
            fraction=0.5,
            anchor_config=anchor_config,
            logger=mock_logger,
        )

        signal = {
            "ticker": "AAPL",
            "signal_type": "sell",
            "price": 120.0,  # 10% above rolling max of 109.0: (120.0 - 109.0) / 109.0 = 10.1% > 10%
            "signal_time": pd.Timestamp("2024-01-05", tz="UTC"),
        }
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        ohlcv = pd.DataFrame(
            {"high": [105.0, 106.0, 107.0, 108.0, 109.0]},
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")),
        )
        context = PositionRuleContext(signal, position, {"AAPL": ohlcv})

        decision = rule.evaluate(context)

        # Should trigger if current price (120.0) is 10% above rolling max (109.0)
        # Profit = (120.0 - 109.0) / 109.0 = 11.0 / 109.0 ≈ 10.1% > 10% threshold
        assert decision.exit_fraction is not None
