# This will eventually use the schwab_api client
from component.software.finance.financial_instrument import FinancialInstrument
import yfinance as yf

class Stock(FinancialInstrument):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger.info(f"Initializing stock {self.ticker}")
        self.data = yf.Ticker(self.ticker)

    def get_name(self) -> str:
        pass

    def get_open(self, timescale: str) -> float:
        pass

    def get_close(self, timescale: str) -> float:
        self.logger.info(f"Getting close for {self.ticker} at {timescale}")
        result = self.data.history(period=timescale)
        return result

    def get_high(self, timescale: str) -> float:
        pass
    
    def get_low(self, timescale: str) -> float:
        pass
