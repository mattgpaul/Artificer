"""Live market data service.

This module provides the LiveMarketService for fetching and caching real-time
stock quotes from Schwab API with automatic refresh based on market hours.
"""

from __future__ import annotations

from system.algo_trader.config import AlgoTraderConfig
from system.algo_trader.service.market_data.base import MarketBase, MarketHoursType
from system.algo_trader.redis.live_market import LiveMarketBroker


class LiveMarketService(MarketBase):
    """Service for collecting and caching live market quote data.

    Fetches real-time stock quotes from Schwab API at regular intervals
    and caches them in Redis. Handles market hours checking and provides
    health check capabilities for monitoring.

    Attributes:
        _market_broker: Live market data Redis broker.
    """

    def __init__(
        self, sleep_override: int | None = None, config: AlgoTraderConfig | None = None
    ) -> None:
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
        """Get the sleep interval for the current market conditions.

        Returns:
            Sleep interval in seconds appropriate for current market hours.
        """
        self.logger.info("Getting sleep interval")

        # Check if there is an override
        if self.sleep_override is not None:
            self.logger.debug(f"Using sleep override: {self.sleep_override} seconds")
            return self.sleep_override

        # Use consolidated market conditions check
        market_conditions = self._get_market_conditions()

        if not market_conditions["is_open"]:
            sleep_interval = 3600  # 1 hour intervals outside market hours
            self.logger.info("1hr intervals (market closed)")
        elif market_conditions["hours_type"] == MarketHoursType.PREMARKET:
            sleep_interval = 300  # 5min intervals
            self.logger.info("5min intervals (premarket)")
        elif market_conditions["hours_type"] == MarketHoursType.STANDARD:
            sleep_interval = 1  # 1 second intervals
            self.logger.info("1s intervals (standard hours)")
        else:
            sleep_interval = 3600  # 1 hour intervals
            self.logger.info("1hr intervals (extended hours)")

        return sleep_interval

    def _execute_pipeline(self) -> bool:
        """Execute the live market data collection pipeline.

        Returns:
            True if pipeline executed successfully, False otherwise.
        """
        try:
            tickers = self.watchlist_broker.get_watchlist()
            self.logger.debug(f"Tickers: {tickers}")

            # Convert set to list for get_quotes method
            ticker_list = list(tickers) if tickers else []

            if not ticker_list:
                self.logger.info("No tickers in watchlist, skipping quotes update")
                return True

            quotes_data = self.api_handler.get_quotes(ticker_list)
            success = self.market_broker.set_quotes(quotes_data)

            if success:
                self.logger.debug(f"Successfully updated quotes for {len(ticker_list)} tickers")
            else:
                self.logger.error("Failed to update quotes in Redis")

            return success

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            return False

    def _check_dependency(self, check_func, error_msg: str) -> bool:
        """Check a dependency and return False if it fails.

        Args:
            check_func: Function to call for the check.
            error_msg: Error message to log if check fails.

        Returns:
            True if check passes, False otherwise.
        """
        try:
            result = check_func()
            if result is False:
                self.logger.error(error_msg)
                return False
            return True
        except Exception as e:
            self.logger.error(f"{error_msg}: {e}")
            return False

    def health_check(self) -> bool:
        """Perform health check on service and dependencies.

        Returns:
            True if service is healthy, False otherwise.
        """
        try:
            # Check if service is running
            if not self.running:
                self.logger.error("Service is not running")
                return False

            # Check API handler connectivity
            if not self._check_dependency(
                lambda: self.api_handler.get_market_hours(), "API handler health check failed"
            ):
                return False

            # Check Redis connectivity
            if not self._check_dependency(
                lambda: self.market_broker.get_market_hours(), "Redis health check failed"
            ):
                return False

            # Check watchlist broker
            if not self._check_dependency(
                lambda: self.watchlist_broker.get_watchlist(),
                "Watchlist broker health check failed",
            ):
                return False

            self.logger.info("Health check passed")
            return True

        except Exception as e:
            self.logger.error(f"Health check failed with unexpected error: {e}")
            return False
