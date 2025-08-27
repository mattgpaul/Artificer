from abc import ABC, abstractmethod
from infrastructure.logging.logger import get_logger
from component.software.finance.stock import Stock
from system.trader.strategy.config import get_config, get_function_config

class Strategy(ABC):
    def __init__(self, stock: Stock) -> None:
        self.stock = stock
        self.logger = get_logger(self.__class__.__name__)
    
    def get_strategy_config(self, defaults: dict = None) -> dict:
        """Get configuration for this strategy class"""
        return get_config(self.__class__.__name__, defaults)
    
    def get_function_config(self, function_name: str, defaults: dict = None) -> dict:
        """Get configuration for a specific function within this strategy"""
        return get_function_config(self.__class__.__name__, function_name, defaults)

    @property
    @abstractmethod
    def buy(self) -> bool:
        pass

    @property
    @abstractmethod
    def sell(self) -> bool:
        pass
