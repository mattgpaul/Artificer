import signal
import time
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from component.software.finance.schema import MarketHours
from infrastructure.logging.logger import get_logger
from system.trader.redis.watchlist import WatchlistBroker
from system.trader.schwab.market_handler import MarketHandler
from system.trader.redis.live_market import LiveMarketBroker

class MarketHoursType(Enum):
    PREMARKET = "premarket"
    STANDARD = "standard"
    EXTENDED = "extended"

class MarketBase(ABC):
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

    def _check_market_open(self, todays_hours: dict[str, str]) -> bool:
        if "start" not in todays_hours.keys():
            self.logger.info("Market not open today")
            return False
        else:
            self.logger.info("Markets are open")
            return True, todays_hours

    def _check_market_hours(self, hours: MarketHours) -> MarketHoursType:
        now = datetime.now(timezone.utc)
        if now < hours.start - timedelta(minutes=5) and now > hours.start - timedelta(hours=2):
            market_hours = MarketHoursType.PREMARKET
        elif now > hours.start - timedelta(minutes=5) and now < hours.end:
            market_hours = MarketHoursType.STANDARD
        else:
            market_hours = MarketHoursType.EXTENDED
        self.logger.info(f"Market hours: {market_hours}")
        return market_hours

    @abstractmethod
    def _get_sleep_interval(self) -> int:
        pass

    @abstractmethod
    def _execute_pipeline(self) -> bool:
        pass

    def run(self):
        self.logger.info(f"Starting {self.__class__.__name__}")

        # Set initial market hours
        self._set_market_hours()
        today = datetime.now(timezone.utc).date()

        while self.running:
            try:
                # Check if we are in a new day
                now = datetime.now(timezone.utc).date()
                if now > today:
                    self.logger.info("New day detected, refreshing market hours")
                    time.sleep(1)
                    self._set_market_hours()
                    today = datetime.now(timezone.utc).date()
                
                # Get sleep interval based on market hours
                sleep_interval = self._get_sleep_interval()
                self.logger.debug(f"Sleep interval set for: {sleep_interval}")

                # Adjust ttl for sleep interval
                self.market_broker.ttl = sleep_interval

                # Execute data pipeline
                try:
                    self._execute_pipeline()
                except Exception as e:
                    self.logger.error(f"Pipeline execution failed: {e}")

                self._sleep_with_interrupt_check(sleep_interval)

            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                self._sleep_with_interrupt_check(60)

        self.logger.info(f"{self.__class__.__name__} shutdown complete")