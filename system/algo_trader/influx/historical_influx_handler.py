import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Union, List

from infrastructure.clients.influx_client import BaseInfluxDBClient

from infrastructure.logging.logger import get_logger

class HistoricalInfluxHandler(BaseInfluxDBClient):
    def __init__(self, database: str = "historical_market_data"):
        super().__init__(database=database)
        self.logger = get_logger(self.__class__.__name__)

    def write_data(self, ticker: list[str], data: list[dict], tags: list[str]) -> bool:
        pass

    