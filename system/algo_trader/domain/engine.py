import uuid
from datetime import datetime, timezone
import time

# Models
from domain.models import (
    MarketOrder,
    Orders,
    Positions,
    PortfolioManager,
    Signals,
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
)
from ports.account_port import AccountPort
from ports.clock_port import ClockPort
from ports.controller_port import ControllerPort

# Ports
from ports.historical_port import HistoricalPort
from ports.journal_port import JournalPort
from ports.order_port import OrderPort
from ports.portfolio_manager_port import PortfolioManagerPort
from ports.quote_port import QuotePort
from ports.strategy_port import StrategyPort


class Engine:
    def __init__(
        self,
        historical_port: HistoricalPort,
        quote_port: QuotePort,
        account_port: AccountPort,
        order_port: OrderPort,
        strategy_port: StrategyPort,
        clock_port: ClockPort,
        portfolio_manager_port: PortfolioManagerPort,
        journal_port: JournalPort,
        controller_port: ControllerPort,
    ):
        self.historical_port = historical_port
        self.quote_port = quote_port
        self.account_port = account_port
        self.order_port = order_port
        self.strategy_port = strategy_port
        self.clock_port = clock_port
        self.portfolio_manager_port = portfolio_manager_port
        self.journal_port = journal_port
        self.controller_port = controller_port
        self._state = EngineState.SETUP

    @staticmethod
    def _signal_filter(signals: Signals, order_instruction: OrderInstruction) -> Signals:
        filtered_signals = []
        for signal in signals.instructions:
            if signal.instruction != order_instruction:
                continue
            filtered_signals.append(signal)
        return filtered_signals

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
                        quantity=position.quantity,
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

    def _filter_signals(self, signals: Signals, portfolio_state: PortfolioManager) -> Signals:
        filtered_signals = []
        if portfolio_state.trading_state == TradingState.BULLISH:
            filtered_signals.extend(self._signal_filter(signals, OrderInstruction.BUY_TO_OPEN))
        elif portfolio_state.trading_state == TradingState.BEARISH:
            filtered_signals.extend(self._signal_filter(signals, OrderInstruction.SELL_TO_OPEN))
        elif portfolio_state.trading_state == TradingState.CLOSE_LONG:
            filtered_signals.extend(self._signal_filter(signals, OrderInstruction.SELL_TO_CLOSE))
        elif portfolio_state.trading_state == TradingState.CLOSE_SHORT:
            filtered_signals.extend(self._signal_filter(signals, OrderInstruction.BUY_TO_CLOSE))
        elif portfolio_state.trading_state == TradingState.NEUTRAL:
            filtered_signals = signals.instructions.copy()
        return Signals(
            timestamp=signals.timestamp,
            instructions=filtered_signals,
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
                self._flatten(position_data)
            else:
                portfolio_state.trading_state = TradingState.DISABLED

        # Get market and account data
        historical_data = self.historical_port.get_data()
        quote_data = self.quote_port.get_quotes()
        account_data = self.account_port.get_account()
        open_orders = self.order_port.get_open_orders()
        portfolio_manager_state = self.portfolio_manager_port.get_state()
        self.journal_port.report_input(
            historical_data,
            quote_data,
            account_data,
            position_data,
            open_orders,
            portfolio_manager_state,
        )

        # Get signals from the strategy
        signals = self.strategy_port.get_signals(
            historical_data,
        )

        # Filter signals based on the portfolio manager's trading state
        signals = self._filter_signals(signals, portfolio_manager_state)

        orders = self.order_port.send_orders(
            signals,
            quote_data,
            account_data,
            position_data,
            open_orders,
        )

        self.journal_port.report_output(
            signals,
            orders,
        )

    def run(self) -> None:
        self._state = EngineState.SETUP
        self.controller_port.publish_status(self._state)

        # Wait for START
        while True:
            cmd = self.controller_port.wait_for_command(timeout_s=None)
            if cmd == ControllerCommand.START:
                self._state = EngineState.RUNNING
                self.controller_port.publish_status(self._state)
                break
            if cmd in (ControllerCommand.STOP, ControllerCommand.EMERGENCY_STOP):
                self._state = EngineState.STOPPED
                self.controller_port.publish_status(self._state)
                return
            # ignore PAUSE/RESUME/NONE in SETUP

        # Main loop
        while self._state not in (EngineState.STOPPED, EngineState.ERROR):
            if self._state == EngineState.RUNNING:
                # Push commands are handled quickly; timeout drives periodic ticks.
                cmd = self.controller_port.wait_for_command(timeout_s=tick_interval_s)

                if cmd == ControllerCommand.PAUSE:
                    self._state = EngineState.PAUSED
                    self.controller_port.publish_status(self._state)
                    continue
                if cmd in (ControllerCommand.STOP, ControllerCommand.EMERGENCY_STOP):
                    self._state = EngineState.STOPPED
                    self.controller_port.publish_status(self._state)
                    break
                if cmd == ControllerCommand.RESUME:
                    # Already running; ignore.
                    continue

                # No command arrived before timeout => do a tick
                if cmd is None:
                    try:
                        self._tick()
                    except Exception as e:
                        self._state = EngineState.ERROR
                        self.controller_port.publish_status(self._state)
                        self.journal_port.report_error(e)
                        break

            elif self._state == EngineState.PAUSED:
                # While paused, do NOT tick. Just wait for resume/stop.
                cmd = self.controller_port.wait_for_command(timeout_s=None)

                if cmd == ControllerCommand.RESUME:
                    self._state = EngineState.RUNNING
                    self.controller_port.publish_status(self._state)
                    continue
                if cmd in (ControllerCommand.STOP, ControllerCommand.EMERGENCY_STOP):
                    self._state = EngineState.STOPPED
                    self.controller_port.publish_status(self._state)
                    break
                # ignore START/PAUSE/NONE while paused

            else:
                # Any unexpected state => stop safely.
                self._state = EngineState.STOPPED
                self.controller_port.publish_status(self._state)
                break

        # Optional: small delay to let logs flush / avoid busy loop in edge cases
        time.sleep(0.01)
