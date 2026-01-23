from ports.historical_port import HistoricalPort
from ports.quote_port import QuotePort
from ports.account_port import AccountPort
from ports.order_port import OrderPort
from ports.strategy_port import StrategyPort
from domain.states import EngineState

class Engine:
    def __init__(
        self,
        historical_port: HistoricalPort,
        quote_port: QuotePort,
        account_port: AccountPort,
        order_port: OrderPort,
        strategy_port: StrategyPort,
        market_status_port: MarketStatusPort,
        manager_port: ManagerPort,
        journal_port: JournalPort,
    ):
        self.historical_port = historical_port
        self.quote_port = quote_port
        self.account_port = account_port
        self.order_port = order_port
        self.strategy_port = strategy_port
        self.manager_port = manager_port
        self.journal_port = journal_port

        self._state = EngineState.SETUP

    def start(self):
        pass

    def stop(self):
        pass

    def pause(self):
        pass

    def resume(self):
        pass

    def _tick(self):
        pass

    def run(self):
        while self._state == EngineState.RUNNING:
            self._tick()
            historical_data = self.historical_port.get_data()
            quote_data = self.quote_port.get_quotes()
            account_data = self.account_port.get_account()
            position_data = self.account_port.get_positions()
            open_orders = self.order_port.get_open_orders()
            manager_state = self.manager_port.get_state()
            self.journal_port.report_input(
                historical_data,
                quote_data,
                account_data,
                position_data,
                open_orders,
                manager_state,
            )

            signals = self.strategy_port.get_signals(
                historical_data,
            )

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



        