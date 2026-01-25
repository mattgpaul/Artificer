"""Unit tests for Engine - Signal filtering and order generation.

Tests cover signal filtering logic, flatten order generation,
and edge cases. All external dependencies are mocked via conftest.py.
"""

import pytest

from system.algo_trader.domain.models import Orders
from system.algo_trader.domain.states import (
    OrderInstruction,
    TradingState,
)


class TestEngineSignalFiltering:
    """Test signal filtering based on trading state."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "trading_state,expected_instructions",
        [
            (TradingState.BULLISH, [OrderInstruction.BUY_TO_OPEN]),
            (TradingState.BEARISH, [OrderInstruction.SELL_TO_OPEN]),
            (TradingState.CLOSE_LONG, [OrderInstruction.SELL_TO_CLOSE]),
            (TradingState.CLOSE_SHORT, [OrderInstruction.BUY_TO_CLOSE]),
            (TradingState.NEUTRAL, [OrderInstruction.BUY_TO_OPEN, OrderInstruction.SELL_TO_OPEN]),
        ],
    )
    def test_filter_signals_by_trading_state(
        self,
        engine_with_fakes,
        sample_market_order,
        trading_state,
        expected_instructions,
    ):
        """Test signal filtering based on trading state."""
        from system.algo_trader.domain.models import PortfolioManager
        from system.algo_trader.domain.states import TradingState

        # Create signals with all instruction types
        signals = Orders(
            timestamp=sample_market_order().timestamp,
            orders=[
                sample_market_order(instruction=OrderInstruction.BUY_TO_OPEN),
                sample_market_order(instruction=OrderInstruction.SELL_TO_OPEN),
                sample_market_order(instruction=OrderInstruction.BUY_TO_CLOSE),
                sample_market_order(instruction=OrderInstruction.SELL_TO_CLOSE),
            ],
        )

        # Set trading state
        portfolio_state = PortfolioManager(
            timestamp=sample_market_order().timestamp,
            trading_state=trading_state,
            max_exposure_pct=100.0,
            max_position_pct=10.0,
        )

        # Filter signals
        filtered = engine_with_fakes._filter_signals(signals, portfolio_state)

        # Verify only expected instructions are present
        if trading_state == TradingState.NEUTRAL:
            # Neutral should pass through all signals
            assert len(filtered.orders) == 4
        else:
            # Other states should filter to specific instruction
            assert len(filtered.orders) == 1
            assert filtered.orders[0].order_instruction in expected_instructions


class TestEngineFlattenOrders:
    """Test flatten order generation for long and short positions."""

    @pytest.mark.unit
    def test_flatten_long_position(self, engine_with_fakes, sample_position):
        """Test flatten generates SELL_TO_CLOSE for long positions."""
        from system.algo_trader.domain.models import Positions

        positions = Positions(
            timestamp=sample_position().timestamp,
            positions=[sample_position(symbol="AAPL", quantity=10)],
        )

        flatten_orders = engine_with_fakes._flatten(positions)

        assert len(flatten_orders.orders) == 1
        assert flatten_orders.orders[0].symbol == "AAPL"
        assert flatten_orders.orders[0].quantity == 10
        assert flatten_orders.orders[0].order_instruction == OrderInstruction.SELL_TO_CLOSE

    @pytest.mark.unit
    def test_flatten_short_position(self, engine_with_fakes, sample_position):
        """Test flatten generates BUY_TO_CLOSE with positive quantity for short positions."""
        from system.algo_trader.domain.models import Positions

        positions = Positions(
            timestamp=sample_position().timestamp,
            positions=[sample_position(symbol="AAPL", quantity=-5)],
        )

        flatten_orders = engine_with_fakes._flatten(positions)

        assert len(flatten_orders.orders) == 1
        assert flatten_orders.orders[0].symbol == "AAPL"
        assert flatten_orders.orders[0].quantity == 5  # Should be positive
        assert flatten_orders.orders[0].order_instruction == OrderInstruction.BUY_TO_CLOSE

    @pytest.mark.unit
    def test_flatten_mixed_positions(self, engine_with_fakes, sample_position):
        """Test flatten handles both long and short positions."""
        from system.algo_trader.domain.models import Positions

        positions = Positions(
            timestamp=sample_position().timestamp,
            positions=[
                sample_position(symbol="AAPL", quantity=10),
                sample_position(symbol="MSFT", quantity=-5),
            ],
        )

        flatten_orders = engine_with_fakes._flatten(positions)

        assert len(flatten_orders.orders) == 2

        # Find AAPL order (long)
        aapl_order = next(o for o in flatten_orders.orders if o.symbol == "AAPL")
        assert aapl_order.quantity == 10
        assert aapl_order.order_instruction == OrderInstruction.SELL_TO_CLOSE

        # Find MSFT order (short)
        msft_order = next(o for o in flatten_orders.orders if o.symbol == "MSFT")
        assert msft_order.quantity == 5  # Should be positive
        assert msft_order.order_instruction == OrderInstruction.BUY_TO_CLOSE

    @pytest.mark.unit
    def test_flatten_empty_positions(self, engine_with_fakes, sample_position):
        """Test flatten handles empty positions gracefully."""
        from system.algo_trader.domain.models import Positions

        positions = Positions(
            timestamp=sample_position().timestamp,
            positions=[],
        )

        flatten_orders = engine_with_fakes._flatten(positions)

        assert len(flatten_orders.orders) == 0

