"""Order port interface.

Defines the interface for order management and execution.
"""

from abc import ABC, abstractmethod

from system.algo_trader.domain.models import (
    Orders,
)


class OrderPort(ABC):
    """Abstract port for order management and execution."""

    @abstractmethod
    def send_orders(self, orders: Orders) -> Orders:
        """Send orders to the broker.

        Args:
            orders: Orders collection to send.

        Returns:
            Orders collection with updated order status.
        """
        ...

    @abstractmethod
    def get_open_orders(self) -> Orders:
        """Retrieve all open orders.

        Returns:
            Orders collection containing open orders.
        """
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a specific order.

        Args:
            order_id: ID of the order to cancel.

        Returns:
            True if cancellation was successful, False otherwise.
        """
        ...

    @abstractmethod
    def cancel_all_orders(self) -> bool:
        """Cancel all open orders.

        Returns:
            True if cancellation was successful, False otherwise.
        """
        ...

    @abstractmethod
    def get_all_orders(self) -> Orders:
        """Retrieve all orders (open, filled, cancelled, etc.).

        Returns:
            Orders collection containing all orders.
        """
        ...
