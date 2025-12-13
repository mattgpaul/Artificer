from enum import StrEnum
from uuid import UUID
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
import pandera as pa
import pandas as pd
from pandera.typing import DataFrame, Index, Series

### Enums ###
class Urgency(StrEnum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"

class OrderEffect(StrEnum):
    BUY_TO_OPEN = "buy_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_OPEN = "sell_to_open"
    SELL_TO_CLOSE = "sell_to_close"

class AssetClass(StrEnum):
    EQUITY = "EQUITY"
    OPTION = "OPTION"
    FUTURES = "FUTURES"

class OptionType(StrEnum):
    CALL = "CALL"
    PUT = "PUT"

### Helper Functions ###

def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(timezone.utc)

#TODO: Add validator at the port once for each symbol at the boundary
class OHLCVSchema(pa.DataFrameModel):
    # columns
    open: Series[float]
    high: Series[float]
    low: Series[float]
    close: Series[float]
    volume: Series[int]

    # index
    index: Index[pa.DateTime]
    @pa.check("index")
    def index_is_utc(cls, idx: pd.DatetimeIndex) -> bool:
        return idx.tz is not None and str(idx.tz) in ("UTC", "UTC+00:00")

    class Config:
        strict = True   # forbid extra columns
        coerce = True   # cast to declared dtypes where possible

class EquityPositionModel(BaseModel):
    symbol: str
    trade_time: datetime
    transaction_id: UUID
    asset_class: AssetClass = AssetClass.EQUITY
    cost_basis: float = Field(gt=0)
    qty: int
    mark: float = Field(gt=0)

    @field_validator("trade_time")  # Trade time must be less than or equal to 'now'
    @classmethod
    def trade_time_not_future(cls, v: datetime) -> datetime:
        now = datetime.now(tz=timezone.utc)
        if v > now:
            raise ValueError("time must be <= now")
        return v

    @field_validator("trade_time")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _ensure_utc(v)

    @field_validator("asset_class")
    @classmethod
    def _must_be_equity(cls, v: AssetClass) -> AssetClass:
        if v != AssetClass.EQUITY:
            raise ValueError("asset_class must be EQUITY for EquityPositionModel")
        return v

class OptionPositionModel(EquityPositionModel):
    asset_class: AssetClass = AssetClass.OPTION
    strike: int = Field(gt=0)
    expiry: datetime
    kind: OptionType

    @field_validator("asset_class")
    @classmethod
    def _must_be_option(cls, v: AssetClass) -> AssetClass:
        if v != AssetClass.OPTION:
            raise ValueError("asset_class must be OPTION for OptionPositionModel")
        return v

class PortfolioModel(BaseModel):
    net_liquidity: float
    available_funds: float
    buying_power: float
    commissions_ytd: float
    open_equity_positions: List[EquityPositionModel]
    open_option_positions: List[OptionPositionModel]

class OrderIntentModel(BaseModel):
    symbol: str
    allocation: float = Field(gt=0, description="Allocation in USD notional")
    max_slippage_pct: float = Field(ge=0, le=0, description="Slippage value should be a fraction")
    deadline: datetime
    allow_partials: bool
    urgency: Urgency
    effect: OrderEffect

    @field_validator("deadline")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _ensure_utc(v)

class MarketTimeModel(BaseModel):
    now: datetime
    market_open: datetime
    market_closed: datetime
    normal_hours: bool
    premarket_hours: bool
    after_hours: bool

    @field_validator("now", "market_open", "market_closed")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _ensure_utc(v)

class OHLCVCollectionModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    data: dict[str, DataFrame[OHLCVSchema]]

class QuotesModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    timestamp: datetime
    data: pd.DataFrame

    @field_validator("timestamp")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _ensure_utc(v)


