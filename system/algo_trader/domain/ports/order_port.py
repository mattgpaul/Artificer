from abc import ABC, abstractmethod

from domain.models import (
    Account,
    Orders,
    Positions,
    Quote,
)


class OrderPort(ABC):
    @abstractmethod
    def send_orders(self, orders: Orders) -> Orders: ...

    @abstractmethod
    def get_open_orders(self) -> Orders: ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: ...

    @abstractmethod
    def cancel_all_orders(self) -> bool: ...

    @abstractmethod
    def get_all_orders(self) -> Orders: ...
