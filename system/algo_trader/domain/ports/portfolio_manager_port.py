"""Portfolio manager port interface.

Defines the interface for portfolio state management and signal processing.
"""

from abc import ABC, abstractmethod

from system.algo_trader.domain.models import Account, Orders, PortfolioManager, Positions, Quote


class PortfolioManagerPort(ABC):
    """Abstract port for portfolio management and signal handling."""

    @abstractmethod
    def get_state(self) -> PortfolioManager:
        """Retrieve current portfolio manager state.

        Returns:
            PortfolioManager object containing current trading state and limits.
        """
        ...

    @abstractmethod
    def handle_signals(  # noqa: PLR0913
        self,
        signals: Orders,
        quote_data: Quote,
        account_data: Account,
        position_data: Positions,
        open_orders: Orders,
        portfolio_state: PortfolioManager,
    ) -> Orders:
        """Process trading signals and generate orders.

        Args:
            signals: Filtered trading signals to process.
            quote_data: Current market quotes.
            account_data: Current account information.
            position_data: Current portfolio positions.
            open_orders: Currently open orders.
            portfolio_state: Current portfolio manager state.

        Returns:
            Orders collection containing generated orders.
        """
        ...
