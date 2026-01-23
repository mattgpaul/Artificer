from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict
import pandas as pd

@dataclass
class HistoricalData:
    period: str
    frequency: str
    start: datetime
    end: datetime
    data: Dict[str,pd.DataFrame]

class HistoricalDataPort(ABC):
    @abstractmethod
    def get_data(self) -> HistoricalData:
        ...