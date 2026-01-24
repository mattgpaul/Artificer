from abc import ABC, abstractmethod

from domain.models import HistoricalOHLCV, Signals


class StrategyPort(ABC):
    @abstractmethod
    def get_signals(self, historical_data: HistoricalOHLCV) -> Signals: ...
