from ports.historical_port import HistoricalPort
from ports.quote_port import QuotePort
from ports.account_port import AccountPort
from ports.order_port import OrderPort

class Engine:
    def __init__(
        self,
        HistoricalPort,
        QuotePort,
        AccountPort,
        StrategyPort,
    ):
        self.historical_port = HistoricalPort
        self.quote_port = QuotePort
        self.account_port = AccountPort
        self.strategy_port = StrategyPort
        self.order_port = OrderPort

    def run(self):
        historical_data = self.historical_port.get_data()
        quote_data = self.quote_port.get_quotes()
        account_data = self.account_port.get_account()
        position_data = self.account_port.get_positions()
        open_orders = self.order_port.get_open_orders()

        signals = self.strategy_port.get_signals(
            historical_data,
        )

        if signals is None:
            return

        orders = self.order_port.send_orders(
            signals,
            quote_data,
            account_data,
            position_data,
            open_orders,
        )

        