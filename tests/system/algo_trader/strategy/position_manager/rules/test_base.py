"""Unit tests for position_manager.rules.base - Base Position Rule Types.

Tests cover AnchorConfig, PositionState, PositionDecision, PositionRuleContext,
PositionRule protocol, and utility functions. All external dependencies are mocked via conftest.py.
"""

import pandas as pd
import pytest

from system.algo_trader.strategy.position_manager.rules.base import (
    AnchorConfig,
    PositionDecision,
    PositionRuleContext,
    PositionState,
    compute_anchor_price,
    validate_exit_signal_and_get_price,
)


class TestAnchorConfig:
    """Test AnchorConfig dataclass."""

    def test_default_values(self):
        """Test AnchorConfig default values."""
        config = AnchorConfig()

        assert config.anchor_type == "entry_price"
        assert config.anchor_field is None
        assert config.lookback_bars is None
        assert config.one_shot is True

    def test_custom_values(self):
        """Test AnchorConfig with custom values."""
        config = AnchorConfig(
            anchor_type="rolling_max",
            anchor_field="high",
            lookback_bars=20,
            one_shot=False,
        )

        assert config.anchor_type == "rolling_max"
        assert config.anchor_field == "high"
        assert config.lookback_bars == 20
        assert config.one_shot is False


class TestPositionState:
    """Test PositionState dataclass."""

    def test_default_values(self):
        """Test PositionState default values."""
        state = PositionState()

        assert state.size == 0.0
        assert state.side is None
        assert state.entry_price is None
        assert state.size_shares == 0.0
        assert state.avg_entry_price == 0.0

    def test_custom_values(self):
        """Test PositionState with custom values."""
        state = PositionState(
            size=1.0,
            side="LONG",
            entry_price=100.0,
            size_shares=100.0,
            avg_entry_price=100.0,
        )

        assert state.size == 1.0
        assert state.side == "LONG"
        assert state.entry_price == 100.0
        assert state.size_shares == 100.0
        assert state.avg_entry_price == 100.0


class TestPositionDecision:
    """Test PositionDecision dataclass."""

    def test_default_values(self):
        """Test PositionDecision default values."""
        decision = PositionDecision()

        assert decision.allow_entry is None
        assert decision.exit_fraction is None
        assert decision.reason is None

    def test_allow_entry_true(self):
        """Test PositionDecision with allow_entry=True."""
        decision = PositionDecision(allow_entry=True)

        assert decision.allow_entry is True

    def test_allow_entry_false(self):
        """Test PositionDecision with allow_entry=False."""
        decision = PositionDecision(allow_entry=False, reason="stop_loss")

        assert decision.allow_entry is False
        assert decision.reason == "stop_loss"

    def test_exit_fraction(self):
        """Test PositionDecision with exit_fraction."""
        decision = PositionDecision(exit_fraction=0.5, reason="take_profit")

        assert decision.exit_fraction == 0.5
        assert decision.reason == "take_profit"


class TestPositionRuleContext:
    """Test PositionRuleContext class."""

    def test_initialization(self):
        """Test PositionRuleContext initialization."""
        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 150.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        ohlcv = {"AAPL": pd.DataFrame({"close": [150.0]})}

        context = PositionRuleContext(signal, position, ohlcv)

        assert context.signal == signal
        assert context.position == position
        assert context.ohlcv_by_ticker == ohlcv

    def test_get_ticker_ohlcv(self):
        """Test get_ticker_ohlcv method."""
        signal = {"ticker": "AAPL"}
        position = PositionState()
        ohlcv = {"AAPL": pd.DataFrame({"close": [150.0]})}

        context = PositionRuleContext(signal, position, ohlcv)

        result = context.get_ticker_ohlcv("AAPL")
        assert result is not None
        assert len(result) == 1

    def test_get_ticker_ohlcv_missing(self):
        """Test get_ticker_ohlcv with missing ticker."""
        signal = {"ticker": "AAPL"}
        position = PositionState()
        ohlcv = {}

        context = PositionRuleContext(signal, position, ohlcv)

        result = context.get_ticker_ohlcv("MSFT")
        assert result is None

    def test_initialization_with_none_ohlcv(self):
        """Test PositionRuleContext initialization with None ohlcv."""
        signal = {"ticker": "AAPL"}
        position = PositionState()

        context = PositionRuleContext(signal, position, None)

        assert context.ohlcv_by_ticker == {}


class TestComputeAnchorPrice:
    """Test compute_anchor_price function."""

    def test_compute_anchor_price_entry_price(self):
        """Test compute_anchor_price with entry_price type."""
        signal = {"ticker": "AAPL", "signal_time": pd.Timestamp("2024-01-01", tz="UTC")}
        position = PositionState(entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        anchor = compute_anchor_price(context, "entry_price", "close")

        assert anchor == 100.0

    def test_compute_anchor_price_rolling_max(self):
        """Test compute_anchor_price with rolling_max type."""
        signal = {"ticker": "AAPL", "signal_time": pd.Timestamp("2024-01-03", tz="UTC")}
        position = PositionState(entry_price=100.0)
        ohlcv = pd.DataFrame(
            {"high": [101.0, 102.0, 103.0]},
            index=pd.DatetimeIndex(
                ["2024-01-01", "2024-01-02", "2024-01-03"], tz="UTC"
            ),
        )
        context = PositionRuleContext(signal, position, {"AAPL": ohlcv})

        anchor = compute_anchor_price(context, "rolling_max", "high")

        assert anchor == 103.0

    def test_compute_anchor_price_rolling_min(self):
        """Test compute_anchor_price with rolling_min type."""
        signal = {"ticker": "AAPL", "signal_time": pd.Timestamp("2024-01-03", tz="UTC")}
        position = PositionState(entry_price=100.0)
        ohlcv = pd.DataFrame(
            {"low": [99.0, 98.0, 97.0]},
            index=pd.DatetimeIndex(
                ["2024-01-01", "2024-01-02", "2024-01-03"], tz="UTC"
            ),
        )
        context = PositionRuleContext(signal, position, {"AAPL": ohlcv})

        anchor = compute_anchor_price(context, "rolling_min", "low")

        assert anchor == 97.0

    def test_compute_anchor_price_with_lookback(self):
        """Test compute_anchor_price with lookback_bars."""
        signal = {"ticker": "AAPL", "signal_time": pd.Timestamp("2024-01-05", tz="UTC")}
        position = PositionState(entry_price=100.0)
        ohlcv = pd.DataFrame(
            {"high": [101.0, 102.0, 103.0, 104.0, 105.0]},
            index=pd.DatetimeIndex(
                ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
                tz="UTC",
            ),
        )
        context = PositionRuleContext(signal, position, {"AAPL": ohlcv})

        anchor = compute_anchor_price(context, "rolling_max", "high", lookback_bars=2)

        assert anchor == 105.0

    def test_compute_anchor_price_missing_ticker(self):
        """Test compute_anchor_price with missing ticker."""
        signal = {}
        position = PositionState(entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        anchor = compute_anchor_price(context, "rolling_max", "high")

        assert anchor is None

    def test_compute_anchor_price_missing_ohlcv(self):
        """Test compute_anchor_price with missing OHLCV."""
        signal = {"ticker": "AAPL"}
        position = PositionState(entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        anchor = compute_anchor_price(context, "rolling_max", "high")

        assert anchor is None

    def test_compute_anchor_price_fallback_to_entry(self):
        """Test compute_anchor_price falls back to entry_price when series is available."""
        signal = {"ticker": "AAPL", "signal_time": pd.Timestamp("2024-01-01", tz="UTC")}
        position = PositionState(entry_price=100.0)
        ohlcv = pd.DataFrame(
            {"high": [101.0, 102.0]},
            index=pd.DatetimeIndex(["2024-01-01", "2024-01-02"], tz="UTC"),
        )
        context = PositionRuleContext(signal, position, {"AAPL": ohlcv})

        # When anchor_type is invalid but series is available, it should fall back to entry_price
        anchor = compute_anchor_price(context, "invalid_type", "high")

        assert anchor == 100.0


class TestValidateExitSignalAndGetPrice:
    """Test validate_exit_signal_and_get_price function."""

    def test_validate_exit_signal_valid_long(self):
        """Test validate_exit_signal with valid LONG exit."""
        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 150.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        price = validate_exit_signal_and_get_price(context, "price")

        assert price == 150.0

    def test_validate_exit_signal_valid_short(self):
        """Test validate_exit_signal with valid SHORT exit."""
        signal = {"ticker": "AAPL", "signal_type": "buy", "price": 90.0}
        position = PositionState(size=1.0, side="SHORT", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        price = validate_exit_signal_and_get_price(context, "price")

        assert price == 90.0

    def test_validate_exit_signal_no_position(self):
        """Test validate_exit_signal with no position."""
        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 150.0}
        position = PositionState(size=0.0)
        context = PositionRuleContext(signal, position, {})

        price = validate_exit_signal_and_get_price(context, "price")

        assert price is None

    def test_validate_exit_signal_no_entry_price(self):
        """Test validate_exit_signal with no entry_price."""
        signal = {"ticker": "AAPL", "signal_type": "sell", "price": 150.0}
        position = PositionState(size=1.0, side="LONG", entry_price=None)
        context = PositionRuleContext(signal, position, {})

        price = validate_exit_signal_and_get_price(context, "price")

        assert price is None

    def test_validate_exit_signal_wrong_signal_type(self):
        """Test validate_exit_signal with wrong signal type."""
        signal = {"ticker": "AAPL", "signal_type": "buy", "price": 150.0}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        price = validate_exit_signal_and_get_price(context, "price")

        assert price is None

    def test_validate_exit_signal_missing_price(self):
        """Test validate_exit_signal with missing price."""
        signal = {"ticker": "AAPL", "signal_type": "sell"}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        price = validate_exit_signal_and_get_price(context, "price")

        assert price is None

    def test_validate_exit_signal_invalid_price(self):
        """Test validate_exit_signal with invalid price."""
        signal = {"ticker": "AAPL", "signal_type": "sell", "price": "invalid"}
        position = PositionState(size=1.0, side="LONG", entry_price=100.0)
        context = PositionRuleContext(signal, position, {})

        price = validate_exit_signal_and_get_price(context, "price")

        assert price is None

