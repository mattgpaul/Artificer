# This will eventually use the schwab_api client
from component.software.finance.financial_instrument import FinancialInstrument
from component.software.finance.timescale_enum import Timescale

class Stock(FinancialInstrument):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger.info(f"Initializing stock {self.ticker}")

    def _get_data(self, timescale: Timescale, period: Timescale = None) -> dict:
        # TODO: Implement this
        # This will likely be an API call to the schwab_api client
        # For now, we'll just return a mock dictionary

        self.logger.info(f"Getting data for {self.ticker} at {timescale, period if period else timescale}")
        if timescale > period:
            raise ValueError(f"Timescale {timescale} is greater than period {period}")
        if timescale == period:
            return self._get_data(timescale)
        else:
            return self._get_data(timescale, period)

    def get_name(self) -> str:
        pass

    def get_open(self, timescale: Timescale) -> float:
        self.logger.debug(f"Getting open for {self.ticker} at {timescale}")
        return self._get_data(timescale)["open"]

    def get_close(self, timescale: Timescale) -> float:
        self.logger.debug(f"Getting close for {self.ticker} at {timescale}")
        return self._get_data(timescale)["close"]

    def get_high(self, timescale: Timescale) -> float:
        self.logger.debug(f"Getting high for {self.ticker} at {timescale}")
        return self._get_data(timescale)["high"]

    def get_low(self, timescale: Timescale) -> float:
        self.logger.debug(f"Getting low for {self.ticker} at {timescale}")
        return self._get_data(timescale)["low"]

    def get_volume(self, timescale: Timescale) -> int:
        self.logger.debug(f"Getting volume for {self.ticker} at {timescale}")
        return self._get_data(timescale)["volume"]

    def get_historical_data(self, timescale: Timescale, period: Timescale) -> dict:
        self.logger.debug(f"Getting historical data for {self.ticker} at {timescale} for {period}")
        return self._get_data(timescale, period)
