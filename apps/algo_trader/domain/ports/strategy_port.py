"""Strategy port interface.

Defines the interface for strategy implementations that generate trading signals.
"""

from abc import ABC, abstractmethod

from system.algo_trader.domain.models import HistoricalOHLCV, Orders, Positions, Quote


class StrategyPort(ABC):
    """Abstract port for strategy signal generation."""

    @abstractmethod
    def get_signals(
        self,
        historical_data: HistoricalOHLCV,
        quote_data: Quote,
        position_data: Positions,
    ) -> Orders:
        """Generate trading signals based on market data.

        Args:
            historical_data: Historical OHLCV market data.
            quote_data: Current market quotes.
            position_data: Current portfolio positions.

        Returns:
            Orders collection containing generated trading signals.
        """
        ...
