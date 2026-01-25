"""Account port interface.

Defines the interface for account data access implementations.
"""

from abc import ABC, abstractmethod

from system.algo_trader.domain.models import Account, Positions


class AccountPort(ABC):
    """Abstract port for account and position data access."""

    @abstractmethod
    def get_account(self) -> Account:
        """Retrieve current account information.

        Returns:
            Account object containing account details and balances.
        """
        ...

    @abstractmethod
    def get_positions(self) -> Positions:
        """Retrieve current portfolio positions.

        Returns:
            Positions collection containing all open positions.
        """
        ...
