from abc import ABC, abstractmethod
from infrastructure.logging.logger import get_logger

class Strategy(ABC):
    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

    @property
    @abstractmethod
    def buy(self) -> bool:
        pass

    @property
    @abstractmethod
    def sell(self) -> bool:
        pass
