from datetime import datetime, timezone
from enum import Enum
import pandas as pd

from system.trader.schwab.timescale_enum import FrequencyType, PeriodType
from component.software.finance.schema import MarketHours
from system.trader.redis.historical_market import HistoricalMarketBroker
from system.trader.service.market_base import MarketBase, MarketHoursType

class IntradayInterval(Enum):
    MIN1 = 1
    MIN5 = 5
    MIN10 = 10
    MIN15 = 15
    MIN30 = 30

class HistoricalMarketService(MarketBase):
    def __init__(self, sleep_override=None):
        super().__init__(sleep_override)
        if sleep_override is not None:
            self.logger.warning("HistoricalMarketService does not use sleep_override")
            self.sleep_override = None
        self.market_broker = HistoricalMarketBroker()  # Overwrite attribute for this service

    def _check_intraday_interval(self, hours: MarketHours) -> IntradayInterval:
        self.logger.debug("Checking intraday interval")
        current_market = self._check_market_hours(hours)
        if current_market != MarketHoursType.STANDARD:
            interval_enum = IntradayInterval.MIN30  # Max value outside market hours (i.e. get everything)
            return interval_enum
        
        now = datetime.now(timezone.utc)
        current_minute = now.minute
        
        # Iterate from largest to smallest interval
        for interval_enum in reversed(IntradayInterval):
            if current_minute % interval_enum.value == 0:
                return interval_enum  # Return the first (largest) match

        self.logger.error("No interval matches")
        return None  # No interval matches


    def _get_sleep_interval(self) -> int:
        self.logger.info("Getting sleep interval")
        todays_hours = self.market_broker.get_market_hours()
        market_open = self._check_market_open(todays_hours)
        if not market_open:
            sleep_interval = 60*60  # 1 hour intervals outside market hours
            return sleep_interval
        todays_hours = MarketHours(**todays_hours)
        self.logger.debug(f"Todays hours: {todays_hours}")
        current_market = self._check_market_hours(todays_hours)

        if current_market != MarketHoursType.STANDARD:
            sleep_interval = 3600  # 1 hour intervals
            self.logger.info("1hr intervals")
        else:
            sleep_interval = 60  # 1 min intervals
            self.logger.info("1min intervals")

        return sleep_interval

    def _execute_pipeline(self):
        pass

    def run(self):
        self.logger.info("Starting Historical Market Service...")
        tickers = self.watchlist_broker.get_watchlist()
        for ticker in tickers:
            self.logger.info(f"Getting historical data for: {ticker}")
            self.market_broker.set_historical(ticker=ticker, data=self.api_handler.get_price_history(ticker))

        return 0

def main():
    """Entry point for running the Historical Market Service."""
    try:
        service = HistoricalMarketService()
        result = service.run()
        # Check redis store
        data = service.market_broker.get_historical('SPY')
        df = pd.DataFrame(data)
        print(df)
        print(f"Successfully processed tickers")
        return result
    except Exception as e:
        print(f"Service failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
