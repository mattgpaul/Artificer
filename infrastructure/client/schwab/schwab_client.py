# Use yfinance for now until my api is ready
import yfinance as yf
import pandas as pd
from component.software.finance.timescale_enum import Timescale
from infrastructure.client.client import Client
from infrastructure.logging.logger import get_logger

class SchwabClient(Client):
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def get_historical_data(self, ticker: str, frequency: Timescale = Timescale.DAY, period: Timescale = Timescale.YEAR) -> pd.DataFrame:
        data = yf.download(ticker, period=period.value, interval=frequency.value)
        
        # Handle MultiIndex columns (yfinance sometimes returns ticker as column level)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)  # Remove ticker level, keep OHLCV level
        
        return data