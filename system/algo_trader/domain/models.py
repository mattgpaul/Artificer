from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

import pandas as pd
from system.algo_trader.domain.states import (
    ControllerCommand,
    EngineState,
    MarketStatus,
    OrderDuration,
    OrderInstruction,
    OrderTaxLotMethod,
    OrderType,
    TradingState,
    EventType,
    TickReason,
)


@dataclass
class Controller:
    timestamp: datetime
    command: ControllerCommand
    status: EngineState


@dataclass
class Event:
    timestamp: datetime
    type: EventType
    command: Optional[ControllerCommand] = None
    reason: Optional[TickReason] = None


@dataclass
class PortfolioManager:
    timestamp: datetime
    trading_state: TradingState
    max_exposure_pct: float
    max_position_pct: float


@dataclass
class MarketHours:
    timestamp: datetime
    status: MarketStatus
    start: datetime
    end: datetime


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
    positions: list[Position]


@dataclass
class HistoricalOHLCV:
    period: str
    frequency: str
    start: datetime
    end: datetime
    data: dict[str, pd.DataFrame]


@dataclass
class Quote:
    timestamp: datetime
    asset_class: str
    bid: dict[str, float]
    ask: dict[str, float]
    bid_size: dict[str, float]
    ask_size: dict[str, float]
    last: dict[str, float]
    volume: dict[str, float]
    change: dict[str, float]
    change_pct: dict[str, float]


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
    orders: list[LimitOrder | MarketOrder | StopOrder | StopLimitOrder]


@dataclass
class JournalInput:
    timestamp: datetime
    historical_data: HistoricalOHLCV
    quote_data: Quote
    account_data: Account
    position_data: Positions
    open_orders: Orders
    portfolio_manager_state: PortfolioManager


@dataclass
class JournalOutput:
    timestamp: datetime
    signals: Orders
    orders: Orders


@dataclass
class JournalError:
    timestamp: datetime
    error: Exception
    engine_state: EngineState
