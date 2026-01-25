"""Domain state enumerations.

This module defines all state enumerations used throughout the trading system,
including engine states, trading states, order types, and event types.
"""

from enum import Enum


class EngineState(Enum):
    """Engine lifecycle states."""

    SETUP = "SETUP"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    TEARDOWN = "TEARDOWN"


class ControllerCommand(Enum):
    """Controller commands for engine control."""

    NONE = "NONE"
    START = "START"
    STOP = "STOP"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class EventType(Enum):
    """Types of events processed by the engine."""

    TICK = "TICK"
    COMMAND = "COMMAND"


class TickReason(Enum):
    """Reasons for tick execution."""

    MANUAL = "MANUAL"
    SCHEDULED = "SCHEDULED"
    MARKET_EVENT = "MARKET_EVENT"
    QUOTE_EVENT = "QUOTE_EVENT"
    ACCOUNT_EVENT = "ACCOUNT_EVENT"
    POSITION_EVENT = "POSITION_EVENT"
    ORDER_EVENT = "ORDER_EVENT"
    PORTFOLIO_EVENT = "PORTFOLIO_EVENT"
    STRATEGY_EVENT = "STRATEGY_EVENT"
    PORTFOLIO_MANAGER_EVENT = "PORTFOLIO_MANAGER_EVENT"
    JOURNAL_EVENT = "JOURNAL_EVENT"
    CONTROLLER_EVENT = "CONTROLLER_EVENT"


class TradingState(Enum):
    """Portfolio trading state indicators."""

    DISABLED = "DISABLED"
    FLATTEN = "FLATTEN"
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    VOLATILE = "VOLATILE"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"


class MarketStatus(Enum):
    """Market session status."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PRE_MARKET = "PRE_MARKET"
    POST_MARKET = "POST_MARKET"
    HALTED = "HALTED"


class OrderInstruction(Enum):
    """Order instruction types."""

    BUY_TO_OPEN = "BUY_TO_OPEN"
    SELL_TO_OPEN = "SELL_TO_OPEN"
    BUY_TO_CLOSE = "BUY_TO_CLOSE"
    SELL_TO_CLOSE = "SELL_TO_CLOSE"


class OrderStatus(Enum):
    """Order execution status."""

    WORKING = "WORKING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderDuration(Enum):
    """Order duration/time in force."""

    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class OrderTaxLotMethod(Enum):
    """Tax lot selection methods."""

    FIFO = "FIFO"
    LIFO = "LIFO"
    HIFO = "HIFO"
    AVG_COST = "AVG_COST"
    SPECIFIC_LOT = "SPECIFIC_LOT"


class OrderType(Enum):
    """Order type classifications."""

    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"
    TRAILING_STOP_LIMIT = "TRAILING_STOP_LIMIT"
