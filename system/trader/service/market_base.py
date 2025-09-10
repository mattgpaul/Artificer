import signal
import time
from datetime import datetime, timedelta, timezone

from component.software.finance.schema import MarketHours
from infrastructure.logging.logger import get_logger
from system.trader.redis.watchlist import WatchlistBroker
from system.trader.schwab.market_handler import MarketHandler
from system.trader.redis.live_market import LiveMarketBroker

class MarketBase:
    def __init__(self, sleep_override=None):
        self.logger = get_logger(self.__class__.__name__)
        self.running = True
        self.sleep_override = sleep_override
        self._setup_signal_handlers()
        self._setup_clients()

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGTERM, self._shutdown_handler)
        signal.signal(signal.SIGINT, self._shutdown_handler)

    def _shutdown_handler(self, signum, frame):
        self.logger.info(f"Received signal {signum}, sutting down gracefully...")
        self.running = False

    def _sleep_with_interrupt_check(self, target_interval: float):
        """Sleep to maintain precise interval timing, accounting for work duration"""
        if not hasattr(self, '_last_cycle_time'):
            self._last_cycle_time = time.time()
        
        # Calculate when the next cycle should start
        next_cycle_time = self._last_cycle_time + target_interval
        current_time = time.time()
        
        # Calculate remaining sleep time
        sleep_duration = next_cycle_time - current_time
        
        if sleep_duration > 0:
            # Use the precise sleep logic we discussed earlier
            check_interval = 0.1
            start_sleep = time.time()
            
            while self.running and (time.time() - start_sleep) < sleep_duration:
                remaining = sleep_duration - (time.time() - start_sleep)
                time.sleep(min(check_interval, max(0, remaining)))
        
        # Update for next cycle
        self._last_cycle_time = next_cycle_time
        
        if not self.running:
            self.logger.info("Shutdown signal received during sleep")

    def _setup_clients(self):
        try:
            self.logger.info("Setting up clients")
            self.api_handler = MarketHandler()
            self.market_broker = LiveMarketBroker()
            self.watchlist_broker = WatchlistBroker()
        except Exception as e:
            self.logger.error(f"Failed to initialize clients: {e}")
            raise

    def _set_market_hours(self) -> None:
        today = datetime.now(timezone.utc).date()
        self.logger.info(f"Setting market hours for: {today.strftime('%Y-%m-%d')}")
        self.market_broker.set_market_hours(self.api_handler.get_market_hours(today))

    def _get_sleep_interval(self) -> int:
        self.logger.info("Getting sleep interval")
        # Check if there is an override
        if self.sleep_override is not None:
            self.logger.debug(f"Using sleep override: {self.sleep_override} seconds")
            return self.sleep_override

        todays_hours = self.market_broker.get_market_hours()
        if "start" not in todays_hours.keys():
            self.logger.info("Market not open today")
            sleep_interval = 60*60  # 1 hour intervals outside market hours
            return sleep_interval
        todays_hours = MarketHours(**todays_hours)
        now = datetime.now(timezone.utc)
        
        # Timings based on fitting into nyquist criterion
        if now < todays_hours.start - timedelta(minutes=5) and now > todays_hours.start - timedelta(hours=2):
            self.logger.info("Pre-market hours")
            sleep_interval = 60*5  # 5min intervals
        elif now > todays_hours.start - timedelta(minutes=5) and now < todays_hours.end:
            self.logger.info("Standard Market hours")
            sleep_interval = 1  # 1 second intervals
        else:
            self.logger.info("Outside Market hours")
            sleep_interval = 60*60  # 1 hour intervals

        return sleep_interval