"""Domain models for trading system.

This module defines all data models used throughout the trading system,
including orders, positions, account data, market data, and journal entries.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import pandas as pd

from system.algo_trader.domain.states import (
    ControllerCommand,
    EngineState,
    EventType,
    MarketStatus,
    OrderDuration,
    OrderInstruction,
    OrderTaxLotMethod,
    OrderType,
    TickReason,
    TradingState,
)


@dataclass
class Controller:
    """Controller state and command model.

    Attributes:
        timestamp: Timestamp of the controller state.
        command: Current controller command.
        status: Current engine state.
    """

    timestamp: datetime
    command: ControllerCommand
    status: EngineState


@dataclass
class Event:
    """Event model for event-driven control flow.

    Attributes:
        timestamp: Event timestamp.
        type: Type of event (TICK or COMMAND).
        command: Controller command (if type is COMMAND).
        reason: Tick reason (if type is TICK).
    """

    timestamp: datetime
    type: EventType
    command: ControllerCommand | None = None
    reason: TickReason | None = None


@dataclass
class PortfolioManager:
    """Portfolio manager state model.

    Attributes:
        timestamp: Timestamp of the state.
        trading_state: Current trading state.
        max_exposure_pct: Maximum exposure percentage.
        max_position_pct: Maximum position percentage.
    """

    timestamp: datetime
    trading_state: TradingState
    max_exposure_pct: float
    max_position_pct: float


@dataclass
class MarketHours:
    """Market hours information model.

    Attributes:
        timestamp: Timestamp of the market hours data.
        status: Current market status.
        start: Market open time.
        end: Market close time.
    """

    timestamp: datetime
    status: MarketStatus
    start: datetime
    end: datetime


@dataclass
class Account:
    """Account information model.

    Attributes:
        timestamp: Timestamp of the account data.
        cash: Available cash balance.
        buying_power: Total buying power.
        position_value: Total value of positions.
        net_liquidation: Net liquidation value.
        commission_and_fees: Total commissions and fees.
    """

    timestamp: datetime
    cash: float
    buying_power: float
    position_value: float
    net_liquidation: float
    commission_and_fees: float


@dataclass
class Position:
    """Individual position model.

    Attributes:
        timestamp: Timestamp of the position data.
        symbol: Trading symbol.
        quantity: Position quantity (positive for long, negative for short).
        cost_basis: Average cost basis per share.
        current_price: Current market price.
        pnl_open: Unrealized profit/loss.
        net_liquidation: Net liquidation value for this position.
    """

    timestamp: datetime
    symbol: str
    quantity: int
    cost_basis: float
    current_price: float
    pnl_open: float
    net_liquidation: float


@dataclass
class Positions:
    """Collection of positions model.

    Attributes:
        timestamp: Timestamp of the positions data.
        positions: List of Position objects.
    """

    timestamp: datetime
    positions: list[Position]


@dataclass
class HistoricalOHLCV:
    """Historical OHLCV (Open, High, Low, Close, Volume) data model.

    Attributes:
        period: Time period covered (e.g., "1Y" for one year).
        frequency: Data frequency (e.g., "1D" for daily).
        start: Start datetime.
        end: End datetime.
        data: Dictionary mapping symbols to OHLCV DataFrames.
    """

    period: str
    frequency: str
    start: datetime
    end: datetime
    data: dict[str, pd.DataFrame]


@dataclass
class Quote:
    """Real-time market quote model.

    Attributes:
        timestamp: Quote timestamp.
        asset_class: Asset class (e.g., "EQUITY").
        bid: Dictionary mapping symbols to bid prices.
        ask: Dictionary mapping symbols to ask prices.
        bid_size: Dictionary mapping symbols to bid sizes.
        ask_size: Dictionary mapping symbols to ask sizes.
        last: Dictionary mapping symbols to last trade prices.
        volume: Dictionary mapping symbols to volumes.
        change: Dictionary mapping symbols to price changes.
        change_pct: Dictionary mapping symbols to percentage changes.
    """

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
    """Limit order model.

    Attributes:
        id: Unique order identifier.
        timestamp: Order creation timestamp.
        symbol: Trading symbol.
        price: Limit price.
        quantity: Order quantity.
        order_type: Type of order.
        order_instruction: Order instruction (BUY/SELL TO OPEN/CLOSE).
        order_duration: Order duration/time in force.
        order_tax_lot_method: Tax lot selection method.
    """

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
    """Market order model.

    Attributes:
        id: Unique order identifier.
        timestamp: Order creation timestamp.
        symbol: Trading symbol.
        quantity: Order quantity.
        order_type: Type of order.
        order_instruction: Order instruction (BUY/SELL TO OPEN/CLOSE).
        order_duration: Order duration/time in force.
        order_tax_lot_method: Tax lot selection method.
    """

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
    """Stop order for stop-loss execution.

    Attributes:
        id: Unique order identifier.
        timestamp: Order creation timestamp.
        symbol: Trading symbol.
        price: Stop price trigger.
        quantity: Order quantity.
        order_type: Type of order.
        order_instruction: Order instruction (BUY/SELL TO OPEN/CLOSE).
        order_duration: Order duration/time in force.
        order_tax_lot_method: Tax lot selection method.
    """

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
    """Stop-limit order combining stop and limit prices.

    Attributes:
        id: Unique order identifier.
        timestamp: Order creation timestamp.
        symbol: Trading symbol.
        stop_price: Stop price trigger.
        limit_price: Limit price for execution.
        quantity: Order quantity.
        order_type: Type of order.
        order_instruction: Order instruction (BUY/SELL TO OPEN/CLOSE).
        order_duration: Order duration/time in force.
        order_tax_lot_method: Tax lot selection method.
    """

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
    """Collection of trading orders.

    Attributes:
        timestamp: Timestamp of the orders collection.
        orders: List of order objects (LimitOrder, MarketOrder, etc.).
    """

    timestamp: datetime
    orders: list[LimitOrder | MarketOrder | StopOrder | StopLimitOrder]


@dataclass
class JournalInput:
    """Journal input data for trading cycle.

    Contains all market and account data used during a trading tick.

    Attributes:
        timestamp: Timestamp of the journal entry.
        historical_data: Historical OHLCV market data.
        quote_data: Current market quotes.
        account_data: Current account information.
        position_data: Current portfolio positions.
        open_orders: Currently open orders.
        portfolio_manager_state: Current portfolio manager state.
    """

    timestamp: datetime
    historical_data: HistoricalOHLCV
    quote_data: Quote
    account_data: Account
    position_data: Positions
    open_orders: Orders
    portfolio_manager_state: PortfolioManager


@dataclass
class JournalOutput:
    """Journal output data for trading cycle.

    Contains signals and orders generated during a trading tick.

    Attributes:
        timestamp: Timestamp of the journal entry.
        signals: Trading signals generated by the strategy.
        orders: Orders sent to the broker.
    """

    timestamp: datetime
    signals: Orders
    orders: Orders


@dataclass
class JournalError:
    """Journal error entry for exception tracking.

    Attributes:
        timestamp: Timestamp when the error occurred.
        error: Exception that was raised.
        engine_state: Engine state when the error occurred.
    """

    timestamp: datetime
    error: Exception
    engine_state: EngineState
