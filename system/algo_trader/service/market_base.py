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
from typing import Any

from infrastructure.logging.logger import get_logger
from system.algo_trader.redis.watchlist import WatchlistBroker
from system.algo_trader.schwab.market_handler import MarketHandler
from system.algo_trader.utils.schema import MarketHours

# Module-level constants for timing
_PREMARKET_START_OFFSET_MINUTES = 5
_PREMARKET_WINDOW_HOURS = 2
_SLEEP_CHECK_INTERVAL_SECONDS = 0.1
_DEFAULT_ERROR_RETRY_SECONDS = 60
_NEW_DAY_SLEEP_SECONDS = 1


class MarketHoursType(Enum):
    PREMARKET = "premarket"
    STANDARD = "standard"
    EXTENDED = "extended"


class MarketBase(ABC):
    """Base class for market data pipeline services.

    Provides common functionality for market data services including signal
    handling for graceful shutdown, timing control with interrupt checking,
    market hours management, and service lifecycle management.

    Attributes:
        logger: Configured logger instance for the service.
        running: Boolean flag indicating if service is currently running.
        sleep_override: Optional override for sleep interval in seconds.
        api_handler: MarketHandler instance for Schwab API calls.
        watchlist_broker: WatchlistBroker for managing stock watchlists.
    """

    def __init__(self, sleep_override: int | None = None) -> None:
        """Initialize market service with optional sleep override.

        Args:
            sleep_override: Optional sleep interval override in seconds.
        """
        self.logger = get_logger(self.__class__.__name__)
        self.running = True
        self.sleep_override = sleep_override
        self._setup_signal_handlers()
        self._setup_clients()

    @property
    @abstractmethod
    def market_broker(self):
        pass

    def _setup_signal_handlers(self) -> None:
        """Configure signal handlers for graceful shutdown.

        Sets up handlers for SIGTERM and SIGINT signals to enable clean
        service termination.
        """
        signal.signal(signal.SIGTERM, self._shutdown_handler)
        signal.signal(signal.SIGINT, self._shutdown_handler)

    def _shutdown_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully.

        Args:
            signum: Signal number received.
            frame: Current stack frame at signal receipt.
        """
        self.logger.info(f"Received signal {signum}, sutting down gracefully...")
        self.running = False

    def _sleep_with_interrupt_check(self, target_interval: float) -> None:
        """Sleep while maintaining precise timing and checking for interrupts.

        Uses precise timing to account for work duration and maintains target
        interval between cycles. Checks for shutdown signals periodically
        during sleep.

        Args:
            target_interval: Target time in seconds between cycle starts.
        """
        if not hasattr(self, "_last_cycle_time"):
            self._last_cycle_time = time.time()

        # Calculate when the next cycle should start
        next_cycle_time = self._last_cycle_time + target_interval
        current_time = time.time()

        # Calculate remaining sleep time
        sleep_duration = next_cycle_time - current_time

        if sleep_duration > 0:
            # Use the precise sleep logic we discussed earlier
            check_interval = _SLEEP_CHECK_INTERVAL_SECONDS
            start_sleep = time.time()

            while self.running and (time.time() - start_sleep) < sleep_duration:
                remaining = sleep_duration - (time.time() - start_sleep)
                time.sleep(min(check_interval, max(0, remaining)))

        # Update for next cycle
        self._last_cycle_time = next_cycle_time

        if not self.running:
            self.logger.info("Shutdown signal received during sleep")

    def _setup_clients(self) -> None:
        """Initialize API clients with proper error handling.

        Sets up MarketHandler for Schwab API calls and WatchlistBroker for
        watchlist management. Logs initialization progress and re-raises
        exceptions with context.

        Raises:
            Exception: If client initialization fails.
        """
        try:
            self.logger.info("Setting up clients")
            self.api_handler = MarketHandler()
            self.watchlist_broker = WatchlistBroker()
        except Exception as e:
            self.logger.error(f"Failed to initialize clients: {e}")
            raise

    def _set_market_hours(self) -> None:
        """Fetch and store current market hours from Schwab API.

        Retrieves market hours for today and stores them in the market broker
        for use in determining service behavior.
        """
        today = datetime.now(timezone.utc).date()
        self.logger.info(f"Setting market hours for: {today.strftime('%Y-%m-%d')}")
        self.market_broker.set_market_hours(self.api_handler.get_market_hours(today))

    def _check_market_open(self, todays_hours: dict[str, str]) -> bool:
        """Check if market is open today based on hours data.

        Args:
            todays_hours: Dictionary containing market hours with 'start' key.

        Returns:
            True if market is open, False otherwise. When True, also returns
            the hours dictionary as second value.
        """
        if "start" not in todays_hours.keys():
            self.logger.info("Market not open today")
            return False
        else:
            self.logger.info("Markets are open")
            return True, todays_hours

    def _check_market_hours(self, hours: MarketHours) -> MarketHoursType:
        """Determine current market hours phase based on time.

        Classifies current time as premarket, standard hours, or extended
        hours trading based on market start and end times.

        Args:
            hours: MarketHours object containing start and end times.

        Returns:
            MarketHoursType enum indicating current phase (PREMARKET, STANDARD,
            or EXTENDED).
        """
        now = datetime.now(timezone.utc)
        premarket_start = hours.start - timedelta(minutes=_PREMARKET_START_OFFSET_MINUTES)
        premarket_window_start = hours.start - timedelta(hours=_PREMARKET_WINDOW_HOURS)

        if now < premarket_start and now > premarket_window_start:
            market_hours = MarketHoursType.PREMARKET
        elif now > premarket_start and now < hours.end:
            market_hours = MarketHoursType.STANDARD
        else:
            market_hours = MarketHoursType.EXTENDED
        self.logger.info(f"Market hours: {market_hours}")
        return market_hours

    @abstractmethod
    def _get_sleep_interval(self) -> int:
        """Get the sleep interval for the current market conditions.

        Returns:
            Sleep interval in seconds appropriate for current market hours.
        """
        pass

    @abstractmethod
    def _execute_pipeline(self) -> bool:
        """Execute the main data processing pipeline.

        Returns:
            True if pipeline executed successfully, False otherwise.
        """
        pass

    def run(self) -> None:
        """Run the main service loop.

        Continuously fetches and processes market data based on market hours,
        with automatic refresh of market hours at day boundaries and graceful
        error handling. Runs until shutdown signal received.
        """
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
                    time.sleep(_NEW_DAY_SLEEP_SECONDS)
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
                self._sleep_with_interrupt_check(_DEFAULT_ERROR_RETRY_SECONDS)

        self.logger.info(f"{self.__class__.__name__} shutdown complete")

    @classmethod
    def main(cls, description: str | None = None) -> int:
        """Generic main entry point for market services.

        Provides command-line interface with run and health check commands,
        logging configuration, and graceful error handling.

        Args:
            description: Optional description for the service CLI.

        Returns:
            Exit code (0 for success, 1 for failure).
        """
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
