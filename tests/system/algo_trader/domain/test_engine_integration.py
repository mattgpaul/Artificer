"""Integration tests for Engine - Tick workflow and port interactions.

Tests cover complete _tick() workflow with fake adapters,
verifying port interactions and journaling.
"""

import pytest

from system.algo_trader.domain.models import Orders, Positions
from system.algo_trader.domain.states import (
    OrderInstruction,
    TradingState,
)


class TestEngineTickWorkflow:
    """Test complete tick workflow with fake adapters."""

    @pytest.mark.integration
    def test_tick_normal_workflow(self, engine_with_fakes, sample_market_order):
        """Test normal tick workflow: data fetch -> signals -> orders."""
        # Setup strategy to return signals
        signals = Orders(
            timestamp=sample_market_order().timestamp,
            orders=[sample_market_order(instruction=OrderInstruction.BUY_TO_OPEN)],
        )
        engine_with_fakes.strategy_port.signals = signals

        # Set portfolio manager to neutral (passes all signals)
        engine_with_fakes.portfolio_manager_port.state.trading_state = TradingState.NEUTRAL

        # Execute tick
        engine_with_fakes._tick()

        # Verify journal input was called
        assert len(engine_with_fakes.journal_port.inputs) == 1
        journal_input = engine_with_fakes.journal_port.inputs[0]
        assert journal_input.historical_data is not None
        assert journal_input.quote_data is not None
        assert journal_input.account_data is not None

        # Verify portfolio manager handled signals
        assert len(engine_with_fakes.portfolio_manager_port.handle_signals_calls) == 1

        # Verify orders were sent
        assert len(engine_with_fakes.order_port.sent_orders) == 1

        # Verify journal output was called
        assert len(engine_with_fakes.journal_port.outputs) == 1
        journal_output = engine_with_fakes.journal_port.outputs[0]
        assert len(journal_output.signals.orders) == 1
        assert len(journal_output.orders.orders) == 1

    @pytest.mark.integration
    def test_tick_disabled_state(self, engine_with_fakes):
        """Test tick does nothing when trading state is DISABLED."""
        # Set portfolio manager to disabled
        engine_with_fakes.portfolio_manager_port.state.trading_state = TradingState.DISABLED

        # Execute tick
        engine_with_fakes._tick()

        # Verify no port interactions occurred
        assert len(engine_with_fakes.journal_port.inputs) == 0
        assert len(engine_with_fakes.portfolio_manager_port.handle_signals_calls) == 0
        assert len(engine_with_fakes.order_port.sent_orders) == 0
        assert len(engine_with_fakes.journal_port.outputs) == 0

    @pytest.mark.integration
    def test_tick_flatten_workflow(self, engine_with_fakes, sample_position):
        """Test flatten workflow: positions -> close orders -> send orders."""
        # Setup positions
        positions = Positions(
            timestamp=sample_position().timestamp,
            positions=[sample_position(symbol="AAPL", quantity=10)],
        )
        engine_with_fakes.account_port.positions = positions

        # Set portfolio manager to flatten
        engine_with_fakes.portfolio_manager_port.state.trading_state = TradingState.FLATTEN

        # Execute tick
        engine_with_fakes._tick()

        # Verify flatten orders were sent
        assert len(engine_with_fakes.order_port.sent_orders) == 1
        sent_orders = engine_with_fakes.order_port.sent_orders[0]
        assert len(sent_orders.orders) == 1
        assert sent_orders.orders[0].symbol == "AAPL"
        assert sent_orders.orders[0].order_instruction == OrderInstruction.SELL_TO_CLOSE

        # Verify journal output was called for flatten
        assert len(engine_with_fakes.journal_port.outputs) == 1
        journal_output = engine_with_fakes.journal_port.outputs[0]
        assert len(journal_output.orders.orders) == 1

        # Verify normal workflow did NOT run (no journal input)
        assert len(engine_with_fakes.journal_port.inputs) == 0
        assert len(engine_with_fakes.portfolio_manager_port.handle_signals_calls) == 0

    @pytest.mark.integration
    def test_tick_flatten_empty_positions(self, engine_with_fakes):
        """Test flatten with no positions does nothing."""
        # Ensure positions are empty
        engine_with_fakes.account_port.positions = engine_with_fakes.account_port.get_positions()

        # Set portfolio manager to flatten
        engine_with_fakes.portfolio_manager_port.state.trading_state = TradingState.FLATTEN

        # Execute tick
        engine_with_fakes._tick()

        # Verify no orders were sent
        assert len(engine_with_fakes.order_port.sent_orders) == 0
        assert len(engine_with_fakes.journal_port.outputs) == 0

    @pytest.mark.integration
    def test_tick_signal_filtering_integration(self, engine_with_fakes, sample_market_order):
        """Test signal filtering works in full tick workflow."""
        # Setup signals with mixed instructions
        signals = Orders(
            timestamp=sample_market_order().timestamp,
            orders=[
                sample_market_order(instruction=OrderInstruction.BUY_TO_OPEN),
                sample_market_order(instruction=OrderInstruction.SELL_TO_OPEN),
            ],
        )
        engine_with_fakes.strategy_port.signals = signals

        # Set portfolio manager to BULLISH (should filter to BUY_TO_OPEN only)
        engine_with_fakes.portfolio_manager_port.state.trading_state = TradingState.BULLISH

        # Execute tick
        engine_with_fakes._tick()

        # Verify portfolio manager received filtered signals
        assert len(engine_with_fakes.portfolio_manager_port.handle_signals_calls) == 1
        filtered_signals, _, _, _, _, _ = (
            engine_with_fakes.portfolio_manager_port.handle_signals_calls[0]
        )
        assert len(filtered_signals.orders) == 1
        assert filtered_signals.orders[0].order_instruction == OrderInstruction.BUY_TO_OPEN
