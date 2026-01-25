from abc import ABC, abstractmethod

from domain.models import HistoricalOHLCV, Orders, Quote, Positions


class StrategyPort(ABC):
    @abstractmethod
    def get_signals(
        self,
        historical_data: HistoricalOHLCV,
        quote_data: Quote,
        position_data: Positions,
    ) -> Orders: ...
