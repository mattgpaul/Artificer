import uuid
from datetime import datetime, timezone

# States
from domain.states import (
    TradingState,
    EngineState,
    ControllerCommand,
    MarketStatus,
    OrderInstruction,
    OrderType,
    OrderDuration,
    OrderTaxLotMethod,
)

# Models
from domain.models import (
    Positions,
    Orders,
    Signals,
    Quote,
    Account,
    HistoricalOHLCV,
    MarketHours,
    MarketOrder,
)

# Ports
from ports.historical_port import HistoricalPort
from ports.quote_port import QuotePort
from ports.account_port import AccountPort
from ports.order_port import OrderPort
from ports.strategy_port import StrategyPort
from ports.portfolio_manager_port import PortfolioManagerPort
from ports.clock_port import ClockPort
from ports.journal_port import JournalPort
from ports.controller_port import ControllerPort


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

        # Filter orders based on the portfolio manager's trading state


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

    def run(self):
        while self._state == EngineState.RUNNING:
            try:
                self._tick()
            except Exception as e:
                self._state = EngineState.ERROR
                self.journal_port.report_error(e)
                break



        