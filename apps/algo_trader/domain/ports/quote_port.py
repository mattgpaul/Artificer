"""Quote port interface.

Defines the interface for real-time market quote access.
"""

from abc import ABC, abstractmethod

from system.algo_trader.domain.models import Quote


class QuotePort(ABC):
    """Abstract port for real-time market quote access."""

    @abstractmethod
    def get_quotes(self) -> Quote:
        """Retrieve current market quotes.

        Returns:
            Quote object containing current bid/ask and market data.
        """
        ...
