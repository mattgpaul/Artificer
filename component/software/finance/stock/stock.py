# This will eventually use the schwab_api client
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from component.software.finance.financial_instrument import FinancialInstrument
from component.software.finance.timescale_enum import Timescale

@dataclass
class StockData:
    ticker: str
    name: str
    open: float
    close: float
    high: float
    low: float
    volume: int
    timestamp: datetime

class Stock(FinancialInstrument):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger.info(f"Initializing stock {self.ticker}")

    @cached_property
    def name(self) -> str:
        return self._fetch_name()

    def _fetch_name(self) -> str:
        # TODO: Implement this
        # This will likely be an API call to the schwab_api client
        # For now, I am assuming it will return a string
        pass

    def get_data(self, frequency: Timescale, period: Timescale = None) -> StockData:
        # TODO: Implement this
        # This will likely be an API call to the schwab_api client
        # For now, I am assuming it will return a dictionary
        pass
