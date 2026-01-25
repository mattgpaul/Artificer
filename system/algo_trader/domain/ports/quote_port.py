from abc import ABC, abstractmethod

from algo_trader.domain.models import Quote


class QuotePort(ABC):
    @abstractmethod
    def get_quotes(self) -> Quote: ...
