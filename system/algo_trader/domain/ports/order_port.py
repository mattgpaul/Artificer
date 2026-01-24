from abc import ABC, abstractmethod

from domain.models import (
    Account,
    Orders,
    Positions,
    Quote,
    Signals,
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
    ) -> Orders: ...

    @abstractmethod
    def get_open_orders(self) -> Orders: ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: ...

    @abstractmethod
    def cancel_all_orders(self) -> bool: ...

    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderStatus: ...
