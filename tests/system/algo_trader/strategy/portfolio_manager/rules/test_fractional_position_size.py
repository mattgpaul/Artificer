"""Unit tests for FractionalPositionSizeRule - Fractional Position Sizing.

Tests cover initialization, equity calculation, position sizing, and error handling.
All external dependencies are mocked via conftest.py.
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from system.algo_trader.strategy.portfolio_manager.rules.base import (
    PortfolioDecision,
    PortfolioPosition,
    PortfolioRuleContext,
    PortfolioState,
)
from system.algo_trader.strategy.portfolio_manager.rules.fractional_position_size import (
    FractionalPositionSizeRule,
)


class TestFractionalPositionSizeRuleInitialization:
    """Test FractionalPositionSizeRule initialization."""

    def test_initialization_default(self, mock_logger):
        """Test initialization with default fraction."""
        rule = FractionalPositionSizeRule(logger=mock_logger)

        assert rule.fraction_of_equity == 0.01
        assert rule.logger == mock_logger

    def test_initialization_custom_fraction(self, mock_logger):
        """Test initialization with custom fraction."""
        rule = FractionalPositionSizeRule(fraction_of_equity=0.05, logger=mock_logger)

        assert rule.fraction_of_equity == 0.05

    def test_from_config_default(self, mock_logger):
        """Test from_config with default parameters."""
        rule = FractionalPositionSizeRule.from_config({}, logger=mock_logger)

        assert rule is not None
        assert rule.fraction_of_equity == 0.01

    def test_from_config_custom(self, mock_logger):
        """Test from_config with custom fraction."""
        rule = FractionalPositionSizeRule.from_config(
            {"fraction_of_equity": 0.02}, logger=mock_logger
        )

        assert rule is not None
        assert rule.fraction_of_equity == 0.02

    def test_from_config_invalid(self, mock_logger):
        """Test from_config with invalid parameters."""
        rule = FractionalPositionSizeRule.from_config(
            {"fraction_of_equity": "invalid"}, logger=mock_logger
        )

        assert rule is None
        mock_logger.error.assert_called()


class TestFractionalPositionSizeRuleEvaluation:
    """Test FractionalPositionSizeRule evaluation."""

    def test_evaluate_non_entry_action(self, mock_logger):
        """Test evaluate with non-entry action."""
        rule = FractionalPositionSizeRule(logger=mock_logger)

        signal = {"action": "sell_to_close", "ticker": "AAPL"}
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is True

    def test_evaluate_entry_with_price(self, mock_logger):
        """Test evaluate with entry action and price."""
        rule = FractionalPositionSizeRule(fraction_of_equity=0.01, logger=mock_logger)

        signal = {
            "action": "buy_to_open",
            "ticker": "AAPL",
            "price": 100.0,
            "signal_time": pd.Timestamp("2024-01-01", tz="UTC"),
        }
        state = PortfolioState(cash_available=100000.0)
        ohlcv = {
            "AAPL": pd.DataFrame(
                {"close": [100.0]}, index=pd.DatetimeIndex(["2024-01-01"], tz="UTC")
            )
        }
        context = PortfolioRuleContext(signal, state, ohlcv)

        decision = rule.evaluate(context)

        assert decision.allow_entry is True
        assert decision.max_shares is not None
        assert decision.max_shares > 0

    def test_evaluate_no_equity(self, mock_logger):
        """Test evaluate with no equity."""
        rule = FractionalPositionSizeRule(fraction_of_equity=0.01, logger=mock_logger)

        signal = {
            "action": "buy_to_open",
            "ticker": "AAPL",
            "price": 100.0,
            "signal_time": pd.Timestamp("2024-01-01", tz="UTC"),
        }
        state = PortfolioState(cash_available=0.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is False
        assert decision.reason == "no_equity_for_position"

    def test_evaluate_zero_target_notional(self, mock_logger):
        """Test evaluate with zero target notional."""
        rule = FractionalPositionSizeRule(fraction_of_equity=0.0, logger=mock_logger)

        signal = {
            "action": "buy_to_open",
            "ticker": "AAPL",
            "price": 100.0,
            "signal_time": pd.Timestamp("2024-01-01", tz="UTC"),
        }
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is False
        assert decision.reason == "zero_target_notional"

    def test_evaluate_zero_shares(self, mock_logger):
        """Test evaluate resulting in zero shares."""
        rule = FractionalPositionSizeRule(fraction_of_equity=0.0001, logger=mock_logger)

        signal = {
            "action": "buy_to_open",
            "ticker": "AAPL",
            "price": 1000.0,
            "signal_time": pd.Timestamp("2024-01-01", tz="UTC"),
        }
        state = PortfolioState(cash_available=100.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is False
        assert decision.reason == "zero_target_shares"

    def test_evaluate_with_existing_positions(self, mock_logger):
        """Test evaluate with existing positions in portfolio."""
        rule = FractionalPositionSizeRule(fraction_of_equity=0.01, logger=mock_logger)

        signal = {
            "action": "buy_to_open",
            "ticker": "MSFT",
            "price": 200.0,
            "signal_time": pd.Timestamp("2024-01-01", tz="UTC"),
        }
        positions = {
            "AAPL": PortfolioPosition(shares=50.0, avg_entry_price=150.0, side="LONG")
        }
        state = PortfolioState(cash_available=100000.0, positions=positions)
        ohlcv = {
            "AAPL": pd.DataFrame(
                {"close": [160.0]}, index=pd.DatetimeIndex(["2024-01-01"], tz="UTC")
            ),
            "MSFT": pd.DataFrame(
                {"close": [200.0]}, index=pd.DatetimeIndex(["2024-01-01"], tz="UTC")
            ),
        }
        context = PortfolioRuleContext(signal, state, ohlcv)

        decision = rule.evaluate(context)

        assert decision.allow_entry is True
        assert decision.max_shares is not None

    def test_evaluate_missing_price(self, mock_logger):
        """Test evaluate with missing price."""
        rule = FractionalPositionSizeRule(logger=mock_logger)

        signal = {"action": "buy_to_open", "ticker": "AAPL"}
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is True

    def test_evaluate_missing_signal_time(self, mock_logger):
        """Test evaluate with missing signal_time."""
        rule = FractionalPositionSizeRule(logger=mock_logger)

        signal = {"action": "buy_to_open", "ticker": "AAPL", "price": 100.0}
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is True

    def test_evaluate_invalid_price(self, mock_logger):
        """Test evaluate with invalid price."""
        rule = FractionalPositionSizeRule(logger=mock_logger)

        signal = {
            "action": "buy_to_open",
            "ticker": "AAPL",
            "price": "invalid",
            "signal_time": pd.Timestamp("2024-01-01", tz="UTC"),
        }
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is True

