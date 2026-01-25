import uuid
from datetime import datetime, timezone
import time

# Models
from domain.models import (
    MarketOrder,
    Orders,
    Positions,
    PortfolioManager,
    JournalError,
    JournalInput,
    JournalOutput,
)

# States
from domain.states import (
    EngineState,
    ControllerCommand,
    OrderDuration,
    OrderInstruction,
    OrderTaxLotMethod,
    OrderType,
    TradingState,
    EventType,
)
from ports.account_port import AccountPort
from ports.controller_port import ControllerPort

# Ports
from ports.historical_port import HistoricalPort
from ports.journal_port import JournalPort
from ports.order_port import OrderPort
from ports.portfolio_manager_port import PortfolioManagerPort
from ports.quote_port import QuotePort
from ports.strategy_port import StrategyPort
from ports.event_port import EventPort


class Engine:
    def __init__(
        self,
        historical_port: HistoricalPort,
        quote_port: QuotePort,
        account_port: AccountPort,
        order_port: OrderPort,
        strategy_port: StrategyPort,
        portfolio_manager_port: PortfolioManagerPort,
        journal_port: JournalPort,
        controller_port: ControllerPort,
        event_port: EventPort,
    ):
        self.historical_port = historical_port
        self.quote_port = quote_port
        self.account_port = account_port
        self.order_port = order_port
        self.strategy_port = strategy_port
        self.portfolio_manager_port = portfolio_manager_port
        self.journal_port = journal_port
        self.controller_port = controller_port
        self.event_port = event_port
        self._state = EngineState.SETUP

    @staticmethod
    def _signal_filter(signals: Orders, order_instruction: OrderInstruction):
        return [o for o in signals.orders if o.order_instruction == order_instruction]

    def _flatten(self, positions: Positions) -> Orders:
        orders = []
        close_long = self._close_long(positions)
        close_short = self._close_short(positions)
        orders.extend(close_long.orders)
        orders.extend(close_short.orders)
        return Orders(
            timestamp=datetime.now(timezone.utc),
            orders=orders,
        )

    def _close_long(self, positions: Positions) -> Orders:
        orders = []
        for position in positions.positions:
            if position.quantity > 0:
                orders.append(
                    MarketOrder(
                        id=uuid.uuid4(),
                        timestamp=datetime.now(timezone.utc),
                        symbol=position.symbol,
                        quantity=position.quantity,
                        order_type=OrderType.MARKET,
                        order_instruction=OrderInstruction.SELL_TO_CLOSE,
                        order_duration=OrderDuration.DAY,
                        order_tax_lot_method=OrderTaxLotMethod.FIFO,
                    )
                )
        return Orders(
            timestamp=datetime.now(timezone.utc),
            orders=orders,
        )

    def _close_short(self, positions: Positions) -> Orders:
        orders = []
        for position in positions.positions:
            if position.quantity < 0:
                orders.append(
                    MarketOrder(
                        id=uuid.uuid4(),
                        timestamp=datetime.now(timezone.utc),
                        symbol=position.symbol,
                        quantity=abs(position.quantity),
                        order_type=OrderType.MARKET,
                        order_instruction=OrderInstruction.BUY_TO_CLOSE,
                        order_duration=OrderDuration.DAY,
                        order_tax_lot_method=OrderTaxLotMethod.FIFO,
                    )
                )
        return Orders(
            timestamp=datetime.now(timezone.utc),
            orders=orders,
        )

    def _filter_signals(self, signals: Orders, portfolio_state: PortfolioManager) -> Orders:
        filtered_signals: list = []
        if portfolio_state.trading_state == TradingState.BULLISH:
            filtered_signals.extend(self._signal_filter(signals, OrderInstruction.BUY_TO_OPEN))
        elif portfolio_state.trading_state == TradingState.BEARISH:
            filtered_signals.extend(self._signal_filter(signals, OrderInstruction.SELL_TO_OPEN))
        elif portfolio_state.trading_state == TradingState.CLOSE_LONG:
            filtered_signals.extend(self._signal_filter(signals, OrderInstruction.SELL_TO_CLOSE))
        elif portfolio_state.trading_state == TradingState.CLOSE_SHORT:
            filtered_signals.extend(self._signal_filter(signals, OrderInstruction.BUY_TO_CLOSE))
        elif portfolio_state.trading_state == TradingState.NEUTRAL:
            filtered_signals = signals.orders.copy()
        return Orders(
            timestamp=signals.timestamp,
            orders=filtered_signals,
        )

    def _tick(self):
        # Get portfolio state
        portfolio_state = self.portfolio_manager_port.get_state()

        # Check if the portfolio manager says we can trade
        if portfolio_state.trading_state == TradingState.DISABLED:
            return

        # Get positions first in case we need to flatten
        position_data = self.account_port.get_positions()
        if portfolio_state.trading_state == TradingState.FLATTEN:
            if len(position_data.positions) > 0:
                flatten_orders = self._flatten(position_data)
                self.order_port.send_orders(flatten_orders)
                self.journal_port.report_output(
                    JournalOutput(
                        timestamp=datetime.now(timezone.utc),
                        signals=Orders(timestamp=datetime.now(timezone.utc), orders=[]),
                        orders=flatten_orders,
                    )
                )
                return
            return

        # Get market and account data
        historical_data = self.historical_port.get_data()
        quote_data = self.quote_port.get_quotes()
        account_data = self.account_port.get_account()
        open_orders = self.order_port.get_open_orders()
        portfolio_manager_state = self.portfolio_manager_port.get_state()
        self.journal_port.report_input(
            JournalInput(
                timestamp=datetime.now(timezone.utc),
                historical_data=historical_data,
                quote_data=quote_data,
                account_data=account_data,
                position_data=position_data,
                open_orders=open_orders,
                portfolio_manager_state=portfolio_manager_state,
            )
        )

        # Get signals from the strategy
        signals = self.strategy_port.get_signals(
            historical_data,
            quote_data,
            position_data,
        )

        # Filter signals based on the portfolio manager's trading state
        signals = self._filter_signals(signals, portfolio_manager_state)

        # Handle signals with the portfolio manager
        orders = self.portfolio_manager_port.handle_signals(
            signals,
            quote_data,
            account_data,
            position_data,
            open_orders,
            portfolio_manager_state,
        )

        # Send orders to the order port
        self.order_port.send_orders(orders)

        self.journal_port.report_output(
            JournalOutput(
                timestamp=datetime.now(timezone.utc),
                signals=signals,
                orders=orders,
            )
        )

    def run(self) -> None:
        self._state = EngineState.SETUP
        self.controller_port.publish_status(self._state)

        # Wait for START
        while True:
            ev = self.event_port.wait_for_event(timeout_s=None)
            if ev is None:
                continue
            if ev.type != EventType.COMMAND:
                continue
            if ev.command == ControllerCommand.START:
                self._state = EngineState.RUNNING
                self.controller_port.publish_status(self._state)
                break
            if ev.command in (ControllerCommand.STOP, ControllerCommand.EMERGENCY_STOP):
                self._state = EngineState.STOPPED
                self.controller_port.publish_status(self._state)
                return

        # Main loop
        while self._state not in (EngineState.STOPPED, EngineState.ERROR):
            ev = self.event_port.wait_for_event(timeout_s=None)
            if ev is None:
                continue

            # Commands ALWAYS take precedence
            if ev.type == EventType.COMMAND:
                if ev.command == ControllerCommand.PAUSE:
                    self._state = EngineState.PAUSED
                    self.controller_port.publish_status(self._state)
                    continue

                if ev.command == ControllerCommand.RESUME:
                    self._state = EngineState.RUNNING
                    self.controller_port.publish_status(self._state)
                    continue

                if ev.command in (ControllerCommand.STOP, ControllerCommand.EMERGENCY_STOP):
                    self._state = EngineState.STOPPED
                    self.controller_port.publish_status(self._state)
                    break

                continue  # ignore NONE/START while running

            # Tick events only do work if RUNNING
            if ev.type == EventType.TICK:
                if self._state != EngineState.RUNNING:
                    continue

                try:
                    self._tick()
                except Exception as e:
                    self._state = EngineState.ERROR
                    self.controller_port.publish_status(self._state)
                    self.journal_port.report_error(
                        JournalError(
                            timestamp=datetime.now(timezone.utc),
                            error=e,
                            engine_state=self._state,
                        )
                    )
                    break

        time.sleep(0.01)
