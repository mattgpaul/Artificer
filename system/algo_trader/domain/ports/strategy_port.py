from abc import ABC, abstractmethod

from domain.models import HistoricalOHLCV, Orders


class StrategyPort(ABC):
    @abstractmethod
    def get_signals(self, historical_data: HistoricalOHLCV) -> Orders: ...
