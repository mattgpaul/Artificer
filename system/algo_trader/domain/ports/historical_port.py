"""Historical data port interface.

Defines the interface for historical market data access.
"""

from abc import ABC, abstractmethod

from system.algo_trader.domain.models import HistoricalOHLCV


class HistoricalPort(ABC):
    """Abstract port for historical market data access."""

    @abstractmethod
    def get_data(self) -> HistoricalOHLCV:
        """Retrieve historical OHLCV market data.

        Returns:
            HistoricalOHLCV object containing historical price data.
        """
        ...
