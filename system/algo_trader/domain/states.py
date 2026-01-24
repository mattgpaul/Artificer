from enum import Enum


class EngineState(Enum):
    SETUP = "SETUP"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    TEARDOWN = "TEARDOWN"


class ControllerCommand(Enum):
    NONE = "NONE"
    START = "START"
    STOP = "STOP"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class TradingState(Enum):
    DISABLED = "DISABLED"
    FLATTEN = "FLATTEN"
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    VOLATILE = "VOLATILE"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"


class MarketStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PRE_OPEN = "PRE_MARKET"
    POST_CLOSE = "POST_MARKET"
    HALTED = "HALTED"


class OrderInstruction(Enum):
    BUY_TO_OPEN = "BUY_TO_OPEN"
    SELL_TO_OPEN = "SELL_TO_OPEN"
    BUY_TO_CLOSE = "BUY_TO_CLOSE"
    SELL_TO_CLOSE = "SELL_TO_CLOSE"


class OrderStatus(Enum):
    WORKING = "WORKING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


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
