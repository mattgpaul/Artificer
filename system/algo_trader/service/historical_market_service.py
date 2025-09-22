from datetime import datetime, timezone
from enum import Enum
import sys

from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType
from component.software.finance.schema import MarketHours
from system.algo_trader.redis.historical_market import HistoricalMarketBroker
from system.algo_trader.service.market_base import MarketBase, MarketHoursType

class IntradayInterval(Enum):
    MIN1 = 1
    MIN5 = 5
    MIN10 = 10
    MIN15 = 15
    MIN30 = 30

class HistoricalMarketService(MarketBase):
    def __init__(self, sleep_override=None):
        self._market_broker = HistoricalMarketBroker()
        super().__init__(sleep_override)
        if sleep_override is not None:
            self.logger.warning("HistoricalMarketService does not use sleep_override")
            self.sleep_override = None

    @property
    def market_broker(self):
        return self._market_broker

    def _check_intraday_interval(self) -> IntradayInterval:
        self.logger.debug("Checking intraday interval")
        #TODO: this is duplicated and messy. See if it can be consolidated
        todays_hours = self.market_broker.get_market_hours()
        market_open = self._check_market_open(todays_hours)
        if not market_open:
            interval_enum = IntradayInterval.MIN30  # Max value outside market hours (i.e. get everything)
            self.logger.info(f"Outside market hours interval: {interval_enum}")
            return interval_enum
        todays_hours = MarketHours(**todays_hours)
        self.logger.debug(f"Todays hours: {todays_hours}")
        current_market = self._check_market_hours(todays_hours)
        if current_market != MarketHoursType.STANDARD:
            interval_enum = IntradayInterval.MIN30  # Max value outside market hours (i.e. get everything)
            self.logger.info(f"Outside market hours interval: {interval_enum}")
            return interval_enum
        
        now = datetime.now(timezone.utc)
        current_minute = now.minute
        
        # Iterate from largest to smallest interval
        for interval_enum in reversed(IntradayInterval):
            if current_minute % interval_enum.value == 0:
                self.logger.info(f"Intraday interval: {interval_enum}")
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

    def _get_frequencies(self, interval: IntradayInterval) -> list[int]:
        self.logger.debug("getting frequencies")
        if interval == IntradayInterval.MIN1:
            frequencies = [1]
        elif interval == IntradayInterval.MIN5:
            frequencies = [1, 5]
        elif interval == IntradayInterval.MIN10:
            frequencies = [1, 5, 10]
        elif interval == IntradayInterval.MIN15:
            frequencies = [1, 5, 10, 15]
        elif interval == IntradayInterval.MIN30:
            frequencies = [1, 5, 10, 15, 30]

        self.logger.info(f"Frequencies to query: {frequencies}")
        return frequencies

    def _execute_pipeline(self):
        # Get the tickers
        tickers = self.watchlist_broker.get_watchlist()
        self.logger.debug(f"Tickers: {tickers}")

        # Get interval and frequencies
        interval = self._check_intraday_interval()
        frequencies = self._get_frequencies(interval)

        # Get historical data and store it
        #TODO: use 5 day period for now. might need to revisit
        #TODO: See if we can optimize this nested loop
        for ticker in tickers:
            for freq in frequencies:
                data = self.api_handler.get_price_history(
                    ticker=ticker,
                    period_type=PeriodType.DAY,
                    period=5,
                    frequency_type=FrequencyType.MINUTE,
                    frequency=freq
                )
                success = self.market_broker.set_historical(ticker=ticker, data=data)
                self.logger.debug(f"Set historical data for {ticker}:{freq}min frequency: {success}")

if __name__ == "__main__":
    sys.exit(HistoricalMarketService.main("Historical Market Data Service"))
