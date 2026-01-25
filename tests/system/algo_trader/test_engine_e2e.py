"""End-to-end tests for Engine - Complete event-driven workflow.

Tests cover Engine.run() with event-driven control flow,
verifying state transitions, command precedence, and tick execution.
"""

import threading
import time

import pytest

from system.algo_trader.domain.models import Event, Orders
from system.algo_trader.domain.states import (
    ControllerCommand,
    EngineState,
    EventType,
    OrderInstruction,
    TickReason,
    TradingState,
)


class TestEngineE2EWorkflow:
    """Test complete Engine.run() workflow with event-driven control."""

    @pytest.mark.e2e
    @pytest.mark.timeout(10)
    def test_start_tick_stop_workflow(self, engine_with_fakes, sample_market_order):
        """Test complete workflow: START -> TICK -> STOP."""
        # Setup strategy to return signals
        signals = Orders(
            timestamp=sample_market_order().timestamp,
            orders=[sample_market_order(instruction=OrderInstruction.BUY_TO_OPEN)],
        )
        engine_with_fakes.strategy_port.signals = signals
        engine_with_fakes.portfolio_manager_port.state.trading_state = TradingState.NEUTRAL

        # Create event sequence: START -> TICK -> STOP
        events = [
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.COMMAND,
                command=ControllerCommand.START,
            ),
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.TICK,
                reason=TickReason.SCHEDULED,
            ),
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.COMMAND,
                command=ControllerCommand.STOP,
            ),
        ]
        engine_with_fakes.event_port.events = events

        # Run engine in a thread (it will block waiting for events)
        engine_thread = threading.Thread(target=engine_with_fakes.run, daemon=True)
        engine_thread.start()

        # Wait for engine to process events
        time.sleep(0.5)

        # Verify state transitions
        assert EngineState.SETUP in engine_with_fakes.controller_port.published_statuses
        assert EngineState.RUNNING in engine_with_fakes.controller_port.published_statuses
        assert EngineState.STOPPED in engine_with_fakes.controller_port.published_statuses

        # Verify tick executed (orders were sent)
        assert len(engine_with_fakes.order_port.sent_orders) >= 1

        # Verify journaling occurred
        assert len(engine_with_fakes.journal_port.inputs) >= 1
        assert len(engine_with_fakes.journal_port.outputs) >= 1

    @pytest.mark.e2e
    @pytest.mark.timeout(10)
    def test_pause_resume_workflow(self, engine_with_fakes, sample_market_order):
        """Test command precedence: PAUSE -> TICK (ignored) -> RESUME -> TICK -> STOP."""
        # Setup strategy to return signals
        signals = Orders(
            timestamp=sample_market_order().timestamp,
            orders=[sample_market_order(instruction=OrderInstruction.BUY_TO_OPEN)],
        )
        engine_with_fakes.strategy_port.signals = signals
        engine_with_fakes.portfolio_manager_port.state.trading_state = TradingState.NEUTRAL

        # Create event sequence: START -> PAUSE -> TICK (ignored) -> RESUME -> TICK -> STOP
        events = [
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.COMMAND,
                command=ControllerCommand.START,
            ),
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.COMMAND,
                command=ControllerCommand.PAUSE,
            ),
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.TICK,
                reason=TickReason.SCHEDULED,
            ),
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.COMMAND,
                command=ControllerCommand.RESUME,
            ),
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.TICK,
                reason=TickReason.SCHEDULED,
            ),
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.COMMAND,
                command=ControllerCommand.STOP,
            ),
        ]
        engine_with_fakes.event_port.events = events

        # Track initial order count
        initial_order_count = len(engine_with_fakes.order_port.sent_orders)

        # Run engine in a thread
        engine_thread = threading.Thread(target=engine_with_fakes.run, daemon=True)
        engine_thread.start()

        # Wait for engine to process events
        time.sleep(0.5)

        # Verify state transitions
        assert EngineState.PAUSED in engine_with_fakes.controller_port.published_statuses
        assert EngineState.RUNNING in engine_with_fakes.controller_port.published_statuses
        assert EngineState.STOPPED in engine_with_fakes.controller_port.published_statuses

        # Verify only one tick executed (the one after RESUME)
        # The tick during PAUSE should have been ignored
        final_order_count = len(engine_with_fakes.order_port.sent_orders)
        assert final_order_count == initial_order_count + 1

    @pytest.mark.e2e
    @pytest.mark.timeout(10)
    def test_emergency_stop(self, engine_with_fakes, sample_market_order):
        """Test emergency stop command stops engine immediately."""
        # Create event sequence: START -> EMERGENCY_STOP
        events = [
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.COMMAND,
                command=ControllerCommand.START,
            ),
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.COMMAND,
                command=ControllerCommand.EMERGENCY_STOP,
            ),
        ]
        engine_with_fakes.event_port.events = events

        # Run engine in a thread
        engine_thread = threading.Thread(target=engine_with_fakes.run, daemon=True)
        engine_thread.start()

        # Wait for engine to process events
        time.sleep(0.5)

        # Verify engine stopped
        assert EngineState.STOPPED in engine_with_fakes.controller_port.published_statuses

        # Verify no ticks executed
        assert len(engine_with_fakes.order_port.sent_orders) == 0

    @pytest.mark.e2e
    @pytest.mark.timeout(10)
    def test_error_handling(self, engine_with_fakes, sample_market_order):
        """Test error handling transitions engine to ERROR state."""

        # Setup strategy to raise an exception
        def failing_get_signals(*args, **kwargs):
            raise ValueError("Test error")

        engine_with_fakes.strategy_port.get_signals = failing_get_signals
        engine_with_fakes.portfolio_manager_port.state.trading_state = TradingState.NEUTRAL

        # Create event sequence: START -> TICK (will error) -> STOP
        events = [
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.COMMAND,
                command=ControllerCommand.START,
            ),
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.TICK,
                reason=TickReason.SCHEDULED,
            ),
            Event(
                timestamp=sample_market_order().timestamp,
                type=EventType.COMMAND,
                command=ControllerCommand.STOP,
            ),
        ]
        engine_with_fakes.event_port.events = events

        # Run engine in a thread
        engine_thread = threading.Thread(target=engine_with_fakes.run, daemon=True)
        engine_thread.start()

        # Wait for engine to process events
        time.sleep(0.5)

        # Verify error state was reached
        assert EngineState.ERROR in engine_with_fakes.controller_port.published_statuses

        # Verify error was journaled
        assert len(engine_with_fakes.journal_port.errors) == 1
        error_entry = engine_with_fakes.journal_port.errors[0]
        assert isinstance(error_entry.error, ValueError)
        assert error_entry.engine_state == EngineState.ERROR
