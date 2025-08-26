from abc import ABC
from infrastructure.logging.logger import get_logger

class FinancialInstrument(ABC):
    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        self.logger = get_logger(self.__class__.__name__)