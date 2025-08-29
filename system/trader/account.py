# Performs account management
from infrastructure.logging.logger import get_logger
from infrastructure.client.schwab.schwab_client import SchwabClient
import pandas as pd

class Account:
    def __init__(self, client: SchwabClient):
        self.client = client
        self.logger = get_logger(self.__class__.__name__)

    @property
    def positions(self) -> pd.DataFrame:
        return self.client.get_positions()
    
    @property
    def buying_power(self) -> float:
        return self.client.get_buying_power()
    
    def execute_trade(self, ticker: str, quantity: int, side: str) -> pd.DataFrame:
        return self.client.execute_trade(ticker, quantity, side)