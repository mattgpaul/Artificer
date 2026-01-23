from abc import ABC, abstractmethod

from domain.models import (
    Account,
    LimitOrder,
    MarketOrder,
    Orders,
    Positions,
    Quote,
    Signals,
    StopLimitOrder,
    StopOrder,
)

class OrderPort(ABC):
    @abstractmethod
    def send_orders(
        self,
        signals: Signals,
        quote_data: Quote,
        account_data: Account,
        position_data: Positions,
        open_orders: Orders,
    ) -> Orders:
        ...

    @abstractmethod
    def get_open_orders(self) -> Orders:
        ...