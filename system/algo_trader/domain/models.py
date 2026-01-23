from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
from uuid import UUID

import pandas as pd

from domain.states import OrderInstruction, OrderType, OrderDuration, OrderTaxLotMethod


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


@dataclass
class HistoricalOHLCV:
    period: str
    frequency: str
    start: datetime
    end: datetime
    data: Dict[str, pd.DataFrame]


@dataclass
class Quote:
    timestamp: datetime
    asset_class: str
    bid: Dict[str, float]
    ask: Dict[str, float]
    bid_size: Dict[str, float]
    ask_size: Dict[str, float]
    last: Dict[str, float]
    volume: Dict[str, float]
    change: Dict[str, float]
    change_pct: Dict[str, float]


@dataclass
class Signal:
    timestamp: datetime
    symbol: str
    instruction: OrderInstruction


@dataclass
class Signals:
    timestamp: datetime
    instructions: List[Signal]


@dataclass
class LimitOrder:
    id: UUID
    timestamp: datetime
    symbol: str
    price: float
    quantity: int
    order_type: OrderType
    order_instruction: OrderInstruction
    order_duration: OrderDuration
    order_tax_lot_method: OrderTaxLotMethod


@dataclass
class MarketOrder:
    id: UUID
    timestamp: datetime
    symbol: str
    quantity: int
    order_type: OrderType
    order_instruction: OrderInstruction
    order_duration: OrderDuration
    order_tax_lot_method: OrderTaxLotMethod


@dataclass
class StopOrder:
    id: UUID
    timestamp: datetime
    symbol: str
    price: float
    quantity: int
    order_type: OrderType
    order_instruction: OrderInstruction
    order_duration: OrderDuration
    order_tax_lot_method: OrderTaxLotMethod


@dataclass
class StopLimitOrder:
    id: UUID
    timestamp: datetime
    symbol: str
    stop_price: float
    limit_price: float
    quantity: int
    order_type: OrderType
    order_instruction: OrderInstruction
    order_duration: OrderDuration
    order_tax_lot_method: OrderTaxLotMethod


@dataclass
class Orders:
    timestamp: datetime
    orders: List[LimitOrder | MarketOrder | StopOrder | StopLimitOrder]

