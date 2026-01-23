from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List

from ports.strategy_port import Signals
from ports.quote_port import Quote
from ports.account_port import Account, Positions
from ports.historical_port import HistoricalOHLCV

class OrderInstruction(Enum):
    BUY_TO_OPEN = "BUY_TO_OPEN"
    SELL_TO_OPEN = "SELL_TO_OPEN"
    BUY_TO_CLOSE = "BUY_TO_CLOSE"
    SELL_TO_CLOSE = "SELL_TO_CLOSE"

class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class OrderDuration(Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"

class OrderTaxLotMethod(Enum):
    FIFO = "FIFO"
    LIFO = "LIFO"
    HIFO = "HIFO"
    AVG_COST = "AVG_COST"
    SPECIFIC_LOT = "SPECIFIC_LOT"

class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"
    TRAILING_STOP_LIMIT = "TRAILING_STOP_LIMIT"

@dataclass
class LimitOrder:
    timestamp: datetime
    symbol: str
    price: float
    quantity: int
    order_type: OrderType.LIMIT
    order_instruction: OrderInstruction
    order_duration: OrderDuration
    order_tax_lot_method: OrderTaxLotMethod

@dataclass
class MarketOrder:
    timestamp: datetime
    symbol: str
    quantity: int
    order_type: OrderType.MARKET
    order_instruction: OrderInstruction
    order_duration: OrderDuration
    order_tax_lot_method: OrderTaxLotMethod

@dataclass
class StopOrder:
    timestamp: datetime
    symbol: str
    price: float
    quantity: int
    order_type: OrderType.STOP
    order_instruction: OrderInstruction
    order_duration: OrderDuration
    order_tax_lot_method: OrderTaxLotMethod

@dataclass
class StopLimitOrder:
    timestamp: datetime
    symbol: str
    stop_price: float
    limit_price: float
    quantity: int
    order_type: OrderType.STOP_LIMIT
    order_instruction: OrderInstruction
    order_duration: OrderDuration
    order_tax_lot_method: OrderTaxLotMethod

@dataclass
class Orders:
    timestamp: datetime
    orders: List[LimitOrder | MarketOrder | StopOrder | StopLimitOrder]

class OrderPort(ABC):
    @abstractmethod
    def send_orders(
        self,
        signals: Signals,
        quote_data: Quote,
        account_data: Account,
        position_data: Positions,
        open_orders: Orders,
    ) -> Orders:
        ...

    @abstractmethod
    def get_open_orders(self) -> Orders:
        ...