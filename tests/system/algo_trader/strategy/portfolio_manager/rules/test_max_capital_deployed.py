"""Unit tests for MaxCapitalDeployedRule - Maximum Capital Deployment Limit.

Tests cover initialization, capital deployment calculation, entry blocking, and error handling.
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
from system.algo_trader.strategy.portfolio_manager.rules.max_capital_deployed import (
    MaxCapitalDeployedRule,
)


class TestMaxCapitalDeployedRuleInitialization:
    """Test MaxCapitalDeployedRule initialization."""

    def test_initialization_default(self, mock_logger):
        """Test initialization with default max_deployed_pct."""
        rule = MaxCapitalDeployedRule(logger=mock_logger)

        assert rule.max_deployed_pct == 0.5
        assert rule.logger == mock_logger

    def test_initialization_custom(self, mock_logger):
        """Test initialization with custom max_deployed_pct."""
        rule = MaxCapitalDeployedRule(max_deployed_pct=0.75, logger=mock_logger)

        assert rule.max_deployed_pct == 0.75

    def test_from_config_default(self, mock_logger):
        """Test from_config with default parameters."""
        rule = MaxCapitalDeployedRule.from_config({}, logger=mock_logger)

        assert rule is not None
        assert rule.max_deployed_pct == 0.5

    def test_from_config_custom(self, mock_logger):
        """Test from_config with custom max_deployed_pct."""
        rule = MaxCapitalDeployedRule.from_config({"max_deployed_pct": 0.6}, logger=mock_logger)

        assert rule is not None
        assert rule.max_deployed_pct == 0.6

    def test_from_config_invalid(self, mock_logger):
        """Test from_config with invalid parameters."""
        rule = MaxCapitalDeployedRule.from_config({"max_deployed_pct": "invalid"}, logger=mock_logger)

        assert rule is None
        mock_logger.error.assert_called()


class TestMaxCapitalDeployedRuleEvaluation:
    """Test MaxCapitalDeployedRule evaluation."""

    def test_evaluate_non_entry_action(self, mock_logger):
        """Test evaluate with non-entry action."""
        rule = MaxCapitalDeployedRule(logger=mock_logger)

        signal = {"action": "sell_to_close", "ticker": "AAPL"}
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is True

    def test_evaluate_below_limit(self, mock_logger):
        """Test evaluate when deployment is below limit."""
        rule = MaxCapitalDeployedRule(max_deployed_pct=0.5, logger=mock_logger)

        signal = {
            "action": "buy_to_open",
            "ticker": "AAPL",
            "price": 100.0,
            "shares": 10.0,
        }
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is True

    def test_evaluate_at_limit(self, mock_logger):
        """Test evaluate when deployment is at limit."""
        rule = MaxCapitalDeployedRule(max_deployed_pct=0.5, logger=mock_logger)

        signal = {
            "action": "buy_to_open",
            "ticker": "AAPL",
            "price": 100.0,
            "shares": 10.0,
        }
        positions = {
            "MSFT": PortfolioPosition(shares=500.0, avg_entry_price=100.0, side="LONG")
        }
        state = PortfolioState(cash_available=50000.0, positions=positions)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is False
        assert "capital_deployed_limit" in decision.reason

    def test_evaluate_above_limit(self, mock_logger):
        """Test evaluate when deployment is above limit."""
        rule = MaxCapitalDeployedRule(max_deployed_pct=0.5, logger=mock_logger)

        signal = {
            "action": "buy_to_open",
            "ticker": "AAPL",
            "price": 100.0,
            "shares": 10.0,
        }
        positions = {
            "MSFT": PortfolioPosition(shares=600.0, avg_entry_price=100.0, side="LONG")
        }
        state = PortfolioState(cash_available=40000.0, positions=positions)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is False

    def test_evaluate_missing_price(self, mock_logger):
        """Test evaluate with missing price."""
        rule = MaxCapitalDeployedRule(logger=mock_logger)

        signal = {"action": "buy_to_open", "ticker": "AAPL", "shares": 10.0}
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is True

    def test_evaluate_missing_shares(self, mock_logger):
        """Test evaluate with missing shares."""
        rule = MaxCapitalDeployedRule(logger=mock_logger)

        signal = {"action": "buy_to_open", "ticker": "AAPL", "price": 100.0}
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is True

    def test_evaluate_invalid_price(self, mock_logger):
        """Test evaluate with invalid price."""
        rule = MaxCapitalDeployedRule(logger=mock_logger)

        signal = {
            "action": "buy_to_open",
            "ticker": "AAPL",
            "price": "invalid",
            "shares": 10.0,
        }
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is True

    def test_evaluate_zero_capital(self, mock_logger):
        """Test evaluate with zero total capital."""
        rule = MaxCapitalDeployedRule(logger=mock_logger)

        signal = {
            "action": "buy_to_open",
            "ticker": "AAPL",
            "price": 100.0,
            "shares": 10.0,
        }
        state = PortfolioState(cash_available=0.0)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is True

    def test_evaluate_with_zero_position_shares(self, mock_logger):
        """Test evaluate with positions that have zero shares."""
        rule = MaxCapitalDeployedRule(logger=mock_logger)

        signal = {
            "action": "buy_to_open",
            "ticker": "AAPL",
            "price": 100.0,
            "shares": 10.0,
        }
        positions = {
            "MSFT": PortfolioPosition(shares=0.0, avg_entry_price=100.0, side="LONG")
        }
        state = PortfolioState(cash_available=100000.0, positions=positions)
        context = PortfolioRuleContext(signal, state, {})

        decision = rule.evaluate(context)

        assert decision.allow_entry is True

