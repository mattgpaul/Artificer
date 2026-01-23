from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
import pandas as pd

@dataclass
class Account:
    timestamp: datetime
    cash: float
    buying_power: float
    position_value: float
    net_liquidation: float
    commission_and_fees: float

@dataclass
class Position:
    timestamp: datetime
    symbol: str
    quantity: int
    cost_basis: float
    current_price: float
    pnl_open: float
    net_liquidation: float

@dataclass
class Positions:
    timestamp: datetime
    positions: List[Position]

class AccountPort(ABC):
    @abstractmethod
    def get_account(self) -> Account:
        ...

    @abstractmethod
    def get_positions(self) -> Positions:
        ...