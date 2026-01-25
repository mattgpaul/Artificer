from abc import ABC, abstractmethod

from algo_trader.domain.models import HistoricalOHLCV


class HistoricalPort(ABC):
    @abstractmethod
    def get_data(self) -> HistoricalOHLCV: ...
