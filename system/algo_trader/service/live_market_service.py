"""Live market data service.

This module provides the LiveMarketService for fetching and caching real-time
stock quotes from Schwab API with automatic refresh based on market hours.
"""

import sys

from system.algo_trader.redis.live_market import LiveMarketBroker
from system.algo_trader.service.market_base import MarketBase, MarketHoursType
from system.algo_trader.utils.schema import MarketHours


class LiveMarketService(MarketBase):
    """Service for collecting and caching live market quote data.

    Fetches real-time stock quotes from Schwab API at regular intervals
    and caches them in Redis. Handles market hours checking and provides
    health check capabilities for monitoring.

    Attributes:
        _market_broker: Live market data Redis broker.
    """

    def __init__(self, sleep_override=None, config=None):
        """Initialize live market data service.

        Args:
            sleep_override: Optional sleep interval override in seconds.
            config: Optional AlgoTraderConfig. If None, uses environment variables.
        """
        super().__init__(sleep_override, config)
        redis_config = self.config.redis if self.config else None
        self._market_broker = LiveMarketBroker(config=redis_config)

    @property
    def market_broker(self):
        """Get the live market data broker instance.

        Returns:
            LiveMarketBroker instance for Redis operations.
        """
        return self._market_broker

    def _get_sleep_interval(self) -> int:
        self.logger.info("Getting sleep interval")
        # Check if there is an override
        if self.sleep_override is not None:
            self.logger.debug(f"Using sleep override: {self.sleep_override} seconds")
            return self.sleep_override

        todays_hours = self.market_broker.get_market_hours()
        market_open = self._check_market_open(todays_hours)
        if not market_open:
            sleep_interval = 60 * 60  # 1 hour intervals outside market hours
            return sleep_interval
        todays_hours = MarketHours(**todays_hours)
        self.logger.debug(f"Todays hours: {todays_hours}")
        current_market = self._check_market_hours(todays_hours)

        if current_market == MarketHoursType.PREMARKET:
            sleep_interval = 60 * 5  # 5min intervals
            self.logger.info("5min intervals")
        elif current_market == MarketHoursType.STANDARD:
            sleep_interval = 1  # 1 second intervals
            self.logger.info("1s intervals")
        else:
            sleep_interval = 60 * 60  # 1 hour intervals
            self.logger.info("1hr intervals")

        return sleep_interval

    def _execute_pipeline(self) -> bool:
        tickers = self.watchlist_broker.get_watchlist()
        self.logger.debug(f"Tickers: {tickers}")

        # Convert set to list for get_quotes method
        ticker_list = list(tickers) if tickers else []

        if not ticker_list:
            self.logger.info("No tickers in watchlist, skipping quotes update")
            return True

        success = self.market_broker.set_quotes(self.api_handler.get_quotes(ticker_list))
        self.logger.debug(f"Set quotes for tickers: {success}")
        return success

    def health_check(self) -> bool:
        """Perform health check on service and dependencies.

        Returns:
            True if service is healthy, False otherwise.
        """
        pass


if __name__ == "__main__":
    sys.exit(LiveMarketService.main("Live Market Data Service"))
