"""Historical market data service.

This module provides the HistoricalMarketService for fetching and storing
historical price data from Schwab API, with caching in Redis and persistence
to InfluxDB.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from system.algo_trader.config import AlgoTraderConfig
from system.algo_trader.influx.market_data_influx import MarketDataInflux
from system.algo_trader.service.market_data.base import MarketBase, MarketHoursType
from system.algo_trader.redis.historical_market import HistoricalMarketBroker
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


class IntradayInterval(Enum):
    """Intraday data collection intervals in minutes.

    Defines supported minute-level intervals for historical market data
    collection during market hours.
    """

    MIN1 = 1
    MIN5 = 5
    MIN10 = 10
    MIN15 = 15
    MIN30 = 30


class HistoricalMarketService(MarketBase):
    """Service for collecting and storing historical market data.

    Fetches historical price data from Schwab API at regular intervals
    and stores it in InfluxDB. Handles market hours checking, intraday
    data collection, and precise timing control.

    Attributes:
        _market_broker: Historical market data Redis broker.
        _influx_handler: InfluxDB client for data storage.
    """

    def __init__(
        self, sleep_override: int | None = None, config: AlgoTraderConfig | None = None
    ) -> None:
        """Initialize historical market data service.

        Args:
            sleep_override: Optional sleep interval override (not used by this service).
            config: Optional AlgoTraderConfig. If None, uses environment variables.
        """
        # Extract configs if provided, otherwise None (will use env vars)
        redis_config = config.redis if config else None
        influx_config = config.influxdb if config else None

        self._market_broker = HistoricalMarketBroker(config=redis_config)
        self._influx_handler = MarketDataInflux(database="market_data", config=influx_config)

        super().__init__(sleep_override, config)
        if sleep_override is not None:
            self.logger.warning("HistoricalMarketService does not use sleep_override")
            self.sleep_override = None

    @property
    def market_broker(self):
        """Get the historical market data broker instance.

        Returns:
            HistoricalMarketBroker instance for Redis operations.
        """
        return self._market_broker

    @property
    def database_handler(self):
        """Get the InfluxDB handler instance.

        Returns:
            MarketDataInflux instance for time-series data storage.
        """
        return self._influx_handler

    def _check_intraday_interval(self) -> IntradayInterval:
        """Determine the appropriate intraday interval based on market conditions.

        Returns:
            IntradayInterval enum indicating the appropriate data collection interval.
        """
        self.logger.debug("Checking intraday interval")

        # Check market conditions using consolidated method
        market_conditions = self._get_market_conditions()

        if (
            not market_conditions["is_open"]
            or market_conditions["hours_type"] != MarketHoursType.STANDARD
        ):
            interval_enum = IntradayInterval.MIN30  # Max value outside market hours
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
        return IntradayInterval.MIN30  # Fallback to max interval

    def _get_sleep_interval(self) -> int:
        """Get the sleep interval for the current market conditions.

        Returns:
            Sleep interval in seconds appropriate for current market hours.
        """
        self.logger.info("Getting sleep interval")

        # Use consolidated market conditions check
        market_conditions = self._get_market_conditions()

        if (
            not market_conditions["is_open"]
            or market_conditions["hours_type"] != MarketHoursType.STANDARD
        ):
            sleep_interval = 3600  # 1 hour intervals
            self.logger.info("1hr intervals")
        else:
            sleep_interval = 60  # 1 min intervals
            self.logger.info("1min intervals")

        return sleep_interval

    def _get_frequencies(self, interval: IntradayInterval) -> list[int]:
        """Get list of frequencies to query based on intraday interval.

        Args:
            interval: IntradayInterval enum indicating current interval.

        Returns:
            List of frequency values in minutes to query.
        """
        self.logger.debug("Getting frequencies")

        # Map intervals to their frequency lists
        frequency_map = {
            IntradayInterval.MIN1: [1],
            IntradayInterval.MIN5: [1, 5],
            IntradayInterval.MIN10: [1, 5, 10],
            IntradayInterval.MIN15: [1, 5, 10, 15],
            IntradayInterval.MIN30: [1, 5, 10, 15, 30],
        }

        frequencies = frequency_map[interval]
        self.logger.info(f"Frequencies to query: {frequencies}")
        return frequencies

    def _execute_pipeline(self) -> bool:
        """Execute the historical data collection pipeline.

        Returns:
            True if pipeline executed successfully, False otherwise.
        """
        try:
            # Get the tickers
            tickers = self.watchlist_broker.get_watchlist()
            self.logger.debug(f"Tickers: {tickers}")

            if not tickers:
                self.logger.info("No tickers in watchlist, skipping historical data collection")
                return True

            # Get interval and frequencies
            interval = self._check_intraday_interval()
            frequencies = self._get_frequencies(interval)

            # Collect historical data for all ticker/frequency combinations
            success_count = 0
            total_requests = len(tickers) * len(frequencies)

            for ticker in tickers:
                for freq in frequencies:
                    try:
                        data = self.api_handler.get_price_history(
                            ticker=ticker,
                            period_type=PeriodType.DAY,
                            period=5,  # 5-day period for historical data
                            frequency_type=FrequencyType.MINUTE,
                            frequency=freq,
                        )
                        success = self.database_handler.write(
                            data=data["candles"],
                            ticker=data["symbol"],
                            table="stock",
                        )
                        if success:
                            success_count += 1
                        self.logger.debug(
                            f"Historical data for {ticker}:{freq}min frequency: {success}"
                        )
                    except Exception as e:
                        self.logger.error(f"Failed to process {ticker}:{freq}min - {e}")

            self.logger.info(
                f"Pipeline completed: {success_count}/{total_requests} requests successful"
            )
            return success_count > 0  # Return True if at least one request succeeded

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            return False
