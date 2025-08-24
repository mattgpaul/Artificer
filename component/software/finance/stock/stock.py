# This will eventually use the schwab_api client
from component.software.finance.financial_instrument import FinancialInstrument
from component.software.finance.timescale_enum import Timescale

class Stock(FinancialInstrument):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger.info(f"Initializing stock {self.ticker}")

    def _get_data(self, timescale: Timescale) -> dict:
        # TODO: Implement this
        # This will likely be an API call to the schwab_api client
        # For now, we'll just return a mock dictionary
        return {
            "open": 150.75,
            "close": 152.25,
            "high": 153.00,
            "low": 149.50,
            "volume": 1000000,
        }

    def get_name(self) -> str:
        pass

    def get_open(self, timescale: Timescale) -> float:
        self.logger.info(f"Getting open for {self.ticker} at {timescale}")
        return self._get_data(timescale)["open"]

    def get_close(self, timescale: Timescale) -> float:
        self.logger.info(f"Getting close for {self.ticker} at {timescale}")
        return self._get_data(timescale)["close"]

    def get_high(self, timescale: Timescale) -> float:
        self.logger.info(f"Getting high for {self.ticker} at {timescale}")
        return self._get_data(timescale)["high"]

    def get_low(self, timescale: Timescale) -> float:
        self.logger.info(f"Getting low for {self.ticker} at {timescale}")
        return self._get_data(timescale)["low"]
