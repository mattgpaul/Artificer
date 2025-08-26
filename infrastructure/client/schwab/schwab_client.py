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
        return yf.download(ticker, period=period, interval=frequency)