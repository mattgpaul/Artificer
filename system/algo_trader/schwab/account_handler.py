"""Schwab account data API handler.

This module provides the AccountHandler class for retrieving account
information, positions, and balances from Schwab's account endpoints.
"""

from typing import Any

from infrastructure.logging.logger import get_logger
from system.algo_trader.schwab.schwab_base import SchwabBase


class AccountHandler(SchwabBase):
    """Schwab Account API Handler.

    Provides methods for retrieving account information, positions, and account-related
    operations. Inherits from SchwabClient for authentication and token management.
    """

    def __init__(self):
        """Initialize AccountHandler with account API endpoint."""
        super().__init__()
        self.account_url = f"{self.base_url}/trader/v1"
        self.logger = get_logger(self.__class__.__name__)
        self.logger.info("AccountHandler initialized successfully")

    def get_accounts(self) -> dict[str, Any]:
        """Get all accounts associated with the authenticated user.

        Returns:
            Dict containing account information
        """
        self.logger.info("Getting account information")

        url = f"{self.account_url}/accounts"
        response = self.make_authenticated_request("GET", url)

        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"Failed to get accounts: {response.status_code} - {response.text}")
            return {}

    def get_account_details(self, account_number: str) -> dict[str, Any]:
        """Get detailed information for a specific account.

        Args:
            account_number: The account number to get details for

        Returns:
            Dict containing detailed account information
        """
        self.logger.info(f"Getting account details for {account_number}")

        url = f"{self.account_url}/accounts/{account_number}"
        response = self.make_authenticated_request("GET", url)

        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(
                f"Failed to get account details: {response.status_code} - {response.text}"
            )
            return {}

    def get_positions(self, account_number: str) -> dict[str, Any]:
        """Get positions for a specific account.

        Args:
            account_number: The account number to get positions for

        Returns:
            Dict containing position information
        """
        self.logger.info(f"Getting positions for account {account_number}")

        url = f"{self.account_url}/accounts/{account_number}/positions"
        response = self.make_authenticated_request("GET", url)

        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"Failed to get positions: {response.status_code} - {response.text}")
            return {}

    def get_orders(self, account_number: str) -> dict[str, Any]:
        """Get orders for a specific account.

        Args:
            account_number: The account number to get orders for

        Returns:
            Dict containing order information
        """
        self.logger.info(f"Getting orders for account {account_number}")

        url = f"{self.account_url}/accounts/{account_number}/orders"
        response = self.make_authenticated_request("GET", url)

        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"Failed to get orders: {response.status_code} - {response.text}")
            return {}

    def place_order(self, account_number: str, order_data: dict[str, Any]) -> dict[str, Any]:
        """Place an order for a specific account.

        Args:
            account_number: The account number to place the order for
            order_data: Dictionary containing order details

        Returns:
            Dict containing order confirmation information
        """
        self.logger.info(f"Placing order for account {account_number}")

        url = f"{self.account_url}/accounts/{account_number}/orders"
        response = self.make_authenticated_request("POST", url, json=order_data)

        if response.status_code in [200, 201]:
            return response.json()
        else:
            self.logger.error(f"Failed to place order: {response.status_code} - {response.text}")
            return {}

    def cancel_order(self, account_number: str, order_id: str) -> bool:
        """Cancel an existing order.

        Args:
            account_number: The account number containing the order
            order_id: The order ID to cancel

        Returns:
            True if cancellation was successful, False otherwise
        """
        self.logger.info(f"Cancelling order {order_id} for account {account_number}")

        url = f"{self.account_url}/accounts/{account_number}/orders/{order_id}"
        response = self.make_authenticated_request("DELETE", url)

        if response.status_code == 200:
            self.logger.info(f"Successfully cancelled order {order_id}")
            return True
        else:
            self.logger.error(f"Failed to cancel order: {response.status_code} - {response.text}")
            return False
