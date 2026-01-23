from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List

from ports.order_port import OrderInstruction
from ports.historical_port import HistoricalOHLCV

@dataclass
class Signal:
    timestamp: datetime
    symbol: str
    instruction: OrderInstruction

@dataclass
class Signals:
    timestamp: datetime
    instructions: List[Signal]

class StrategyPort(ABC):
    @abstractmethod
    def get_signals(self, historical_data: HistoricalOHLCV) -> Signals:
        ...