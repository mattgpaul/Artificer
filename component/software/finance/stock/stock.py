# This will eventually use the schwab_api client
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from component.software.finance.financial_instrument import FinancialInstrument
from component.software.finance.timescale_enum import Timescale
from infrastructure.client.schwab.schwab_client import SchwabClient
import pandas as pd

@dataclass
class StockData:
    ticker: str
    name: str

@dataclass
class StockLastData(StockData):
    last: float
    bid: float
    ask: float
    volume: float
    timestamp: datetime

@dataclass
class StockHistoricalData(StockData):
    data: pd.DataFrame
    frequency: Timescale
    
    @property
    def open(self) -> pd.Series:
        return self.data["Open"]
    
    @property
    def high(self) -> pd.Series:
        return self.data["High"]
    
    @property
    def low(self) -> pd.Series:
        return self.data["Low"]
    
    @property
    def close(self) -> pd.Series:
        return self.data["Close"]
    
    @property
    def volume(self) -> pd.Series:
        return self.data["Volume"]
    
    @property
    def timestamp(self) -> pd.Series:
        return self.data["Date"]  #TODO: Convert to timestamp

class Stock(FinancialInstrument):
    def __init__(self, ticker: str, *args, **kwargs):
        super().__init__(ticker,*args, **kwargs)
        self.ticker = ticker.upper()
        self.client = SchwabClient()

        self.logger.info(f"Initializing stock {self.ticker}")

    def get_last(self) -> StockLastData:
        pass

    def get_historical():
        pass
