from abc import ABC, abstractmethod

from domain.models import Quote


class QuotePort(ABC):
    @abstractmethod
    def get_quotes(self) -> Quote:
        ...