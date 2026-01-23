from abc import ABC, abstractmethod

from domain.models import HistoricalOHLCV


class HistoricalPort(ABC):
    @abstractmethod
    def get_data(self) -> HistoricalOHLCV:
        ...