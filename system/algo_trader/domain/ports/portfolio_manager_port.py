from abc import ABC, abstractmethod

from system.algo_trader.domain.models import PortfolioManager, Orders, Quote, Account, Positions

class PortfolioManagerPort(ABC):
    @abstractmethod
    def get_state(self) -> PortfolioManager: ...

    @abstractmethod
    def handle_signals(
        self,
        signals: Orders,
        quote_data: Quote,
        account_data: Account,
        position_data: Positions,
        open_orders: Orders,
        portfolio_state: PortfolioManager,
    ) -> Orders: ...