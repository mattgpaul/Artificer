"""Base class for market data services.

This module provides the MarketBase abstract class with common functionality
for market data pipeline services, including signal handling, market hours
management, timing control, and service lifecycle management.
"""

import argparse
import signal
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from enum import Enum

from infrastructure.logging.logger import get_logger
from system.algo_trader.redis.watchlist import WatchlistBroker
from system.algo_trader.schwab.market_handler import MarketHandler
from system.algo_trader.utils.schema import MarketHours


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

    @property
    @abstractmethod
    def market_broker(self):
        pass

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGTERM, self._shutdown_handler)
        signal.signal(signal.SIGINT, self._shutdown_handler)

    def _shutdown_handler(self, signum, frame):
        self.logger.info(f"Received signal {signum}, sutting down gracefully...")
        self.running = False

    def _sleep_with_interrupt_check(self, target_interval: float):
        """Sleep to maintain precise interval timing, accounting for work duration"""
        if not hasattr(self, "_last_cycle_time"):
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
                    self.logger.info("Pipeline execution complete")
                except Exception as e:
                    self.logger.error(f"Pipeline execution failed: {e}")

                self.logger.info(f"Sleeping for {sleep_interval} seconds")
                self._sleep_with_interrupt_check(sleep_interval)

            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                self._sleep_with_interrupt_check(60)

        self.logger.info(f"{self.__class__.__name__} shutdown complete")

    @classmethod
    def main(cls, description: str = None):
        """Generic main method for all market services"""
        parser = argparse.ArgumentParser(description=description or f"{cls.__name__} Service")
        parser.add_argument(
            "command",
            nargs="?",
            default="run",
            choices=["run", "health"],
            help="Command to execute (default: run)",
        )
        parser.add_argument(
            "--log-level",
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help="Set logging level",
        )
        parser.add_argument(
            "--sleep-interval", type=int, default=None, help="Override sleep interval in seconds"
        )

        args = parser.parse_args()

        try:
            service = cls(sleep_override=args.sleep_interval)

            if args.command == "run":
                service.logger.info(f"Starting {cls.__name__.lower()}...")
                if args.sleep_interval:
                    service.logger.info(f"Using fixed sleep interval: {args.sleep_interval}")
                service.run()
                return 0
            elif args.command == "health":
                if service.health_check():
                    service.logger.info("Health check passed")
                    return 0

        except KeyboardInterrupt:
            print("Service interrupted by user")
            return 0
        except Exception as e:
            print(f"Service failed to start: {e}")
            return 1
