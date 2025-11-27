"""Unit tests for portfolio_manager.rules.base - Base Portfolio Rule Types.

Tests cover PortfolioState, PortfolioDecision, PortfolioRuleContext, PortfolioRule protocol,
and PortfolioRulePipeline. All external dependencies are mocked via conftest.py.
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from system.algo_trader.strategy.portfolio_manager.rules.base import (
    PortfolioDecision,
    PortfolioPosition,
    PortfolioRuleContext,
    PortfolioRulePipeline,
    PortfolioState,
)


class TestPortfolioPosition:
    """Test PortfolioPosition dataclass."""

    def test_default_values(self):
        """Test PortfolioPosition default values."""
        pos = PortfolioPosition()

        assert pos.shares == 0.0
        assert pos.avg_entry_price == 0.0
        assert pos.side is None

    def test_custom_values(self):
        """Test PortfolioPosition with custom values."""
        pos = PortfolioPosition(shares=100.0, avg_entry_price=150.0, side="LONG")

        assert pos.shares == 100.0
        assert pos.avg_entry_price == 150.0
        assert pos.side == "LONG"


class TestPortfolioState:
    """Test PortfolioState dataclass."""

    def test_initialization_with_cash(self):
        """Test PortfolioState initialization with cash."""
        state = PortfolioState(cash_available=100000.0)

        assert state.cash_available == 100000.0
        assert state.positions == {}
        assert state.pending_settlements == {}

    def test_initialization_with_positions(self):
        """Test PortfolioState initialization with positions."""
        positions = {"AAPL": PortfolioPosition(shares=100.0, avg_entry_price=150.0, side="LONG")}
        state = PortfolioState(cash_available=100000.0, positions=positions)

        assert state.cash_available == 100000.0
        assert len(state.positions) == 1
        assert "AAPL" in state.positions

    def test_initialization_with_settlements(self):
        """Test PortfolioState initialization with pending settlements."""
        settlements = {pd.Timestamp("2024-01-01", tz="UTC"): 5000.0}
        state = PortfolioState(cash_available=100000.0, pending_settlements=settlements)

        assert len(state.pending_settlements) == 1
        assert pd.Timestamp("2024-01-01", tz="UTC") in state.pending_settlements


class TestPortfolioDecision:
    """Test PortfolioDecision dataclass."""

    def test_default_values(self):
        """Test PortfolioDecision default values."""
        decision = PortfolioDecision()

        assert decision.allow_entry is None
        assert decision.max_shares is None
        assert decision.reason is None

    def test_allow_entry_true(self):
        """Test PortfolioDecision with allow_entry=True."""
        decision = PortfolioDecision(allow_entry=True)

        assert decision.allow_entry is True

    def test_allow_entry_false_with_reason(self):
        """Test PortfolioDecision with allow_entry=False and reason."""
        decision = PortfolioDecision(allow_entry=False, reason="insufficient_capital")

        assert decision.allow_entry is False
        assert decision.reason == "insufficient_capital"

    def test_max_shares(self):
        """Test PortfolioDecision with max_shares."""
        decision = PortfolioDecision(allow_entry=True, max_shares=100.0)

        assert decision.max_shares == 100.0


class TestPortfolioRuleContext:
    """Test PortfolioRuleContext class."""

    def test_initialization(self):
        """Test PortfolioRuleContext initialization."""
        signal = {"ticker": "AAPL", "price": 150.0}
        state = PortfolioState(cash_available=100000.0)
        ohlcv = {"AAPL": pd.DataFrame({"close": [150.0]})}

        context = PortfolioRuleContext(signal, state, ohlcv)

        assert context.signal == signal
        assert context.portfolio_state == state
        assert context.ohlcv_by_ticker == ohlcv

    def test_get_ticker_ohlcv(self):
        """Test get_ticker_ohlcv method."""
        signal = {"ticker": "AAPL"}
        state = PortfolioState(cash_available=100000.0)
        ohlcv = {"AAPL": pd.DataFrame({"close": [150.0]})}

        context = PortfolioRuleContext(signal, state, ohlcv)

        result = context.get_ticker_ohlcv("AAPL")
        assert result is not None
        assert len(result) == 1

    def test_get_ticker_ohlcv_missing(self):
        """Test get_ticker_ohlcv with missing ticker."""
        signal = {"ticker": "AAPL"}
        state = PortfolioState(cash_available=100000.0)
        ohlcv = {}

        context = PortfolioRuleContext(signal, state, ohlcv)

        result = context.get_ticker_ohlcv("MSFT")
        assert result is None

    def test_initialization_with_none_ohlcv(self):
        """Test PortfolioRuleContext initialization with None ohlcv."""
        signal = {"ticker": "AAPL"}
        state = PortfolioState(cash_available=100000.0)

        context = PortfolioRuleContext(signal, state, None)

        assert context.ohlcv_by_ticker == {}


class TestPortfolioRulePipeline:
    """Test PortfolioRulePipeline class."""

    def test_initialization(self, mock_logger):
        """Test PortfolioRulePipeline initialization."""
        rules = []
        pipeline = PortfolioRulePipeline(rules, logger=mock_logger)

        assert pipeline.rules == rules
        assert pipeline.logger == mock_logger

    def test_decide_entry_all_allow(self, mock_logger):
        """Test decide_entry when all rules allow entry."""
        rule1 = MagicMock()
        rule1.evaluate.return_value = PortfolioDecision(allow_entry=True)
        rule2 = MagicMock()
        rule2.evaluate.return_value = PortfolioDecision(allow_entry=True, max_shares=100.0)

        pipeline = PortfolioRulePipeline([rule1, rule2], logger=mock_logger)

        signal = {"ticker": "AAPL"}
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        allow, max_shares, reason = pipeline.decide_entry(context)

        assert allow is True
        assert max_shares == 100.0

    def test_decide_entry_one_rejects(self, mock_logger):
        """Test decide_entry when one rule rejects entry."""
        rule1 = MagicMock()
        rule1.evaluate.return_value = PortfolioDecision(allow_entry=True)
        rule2 = MagicMock()
        rule2.evaluate.return_value = PortfolioDecision(allow_entry=False, reason="insufficient_capital")

        pipeline = PortfolioRulePipeline([rule1, rule2], logger=mock_logger)

        signal = {"ticker": "AAPL"}
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        allow, max_shares, reason = pipeline.decide_entry(context)

        assert allow is False
        assert reason == "insufficient_capital"

    def test_decide_entry_min_max_shares(self, mock_logger):
        """Test decide_entry takes minimum of max_shares from multiple rules."""
        rule1 = MagicMock()
        rule1.evaluate.return_value = PortfolioDecision(allow_entry=True, max_shares=100.0)
        rule2 = MagicMock()
        rule2.evaluate.return_value = PortfolioDecision(allow_entry=True, max_shares=50.0)

        pipeline = PortfolioRulePipeline([rule1, rule2], logger=mock_logger)

        signal = {"ticker": "AAPL"}
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        allow, max_shares, reason = pipeline.decide_entry(context)

        assert allow is True
        assert max_shares == 50.0

    def test_decide_entry_exception_handling(self, mock_logger):
        """Test decide_entry handles exceptions from rules."""
        rule1 = MagicMock()
        rule1.evaluate.side_effect = Exception("Test error")

        pipeline = PortfolioRulePipeline([rule1], logger=mock_logger)

        signal = {"ticker": "AAPL"}
        state = PortfolioState(cash_available=100000.0)
        context = PortfolioRuleContext(signal, state, {})

        allow, max_shares, reason = pipeline.decide_entry(context)

        assert allow is False
        assert max_shares is None
        mock_logger.warning.assert_called()

