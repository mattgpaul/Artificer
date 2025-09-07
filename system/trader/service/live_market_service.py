import sys
import signal
import argparse
import time
from datetime import datetime, timedelta

from component.software.finance.schema import MarketHours
from infrastructure.logging.logger import get_logger
from system.trader.redis.watchlist import WatchlistBroker
from system.trader.schwab.market_handler import MarketHandler
from system.trader.redis.live_market import LiveMarketBroker
from system.trader.test_data_pipeline import today

class LiveMarketService:
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
        today = datetime.now().date()
        self.logger.info(f"Setting market hours for: {today.strftime("%Y-%m-%d")}")
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
        todays_hours = MarketHours(**todays_hours)
        now = datetime.now()
        
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

    def _execute_pipeline(self) -> bool:
        tickers = self.watchlist_broker.get_watchlist()
        self.logger.debug(f"Tickers: {tickers}")

        success = self.market_broker.set_quotes(self.api_handler.get_quotes(tickers))
        self.logger.debug(f"Set quotes for tickers: {success}")

    def run(self):
        self.logger.info("Starting LiveMarketService")

        # Set initial market hours
        self._set_market_hours()
        today = datetime.now().date()

        while self.running:
            try:
                # Check if we are in a new day
                now = datetime.now().date()
                if now > today:
                    self.logger.info("New day detected, refreshing market hours")
                    time.sleep(1)
                    self._set_market_hours()
                    today = datetime.now().date()
                
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

                time.sleep(sleep_interval)

            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(60)

        self.logger.info("LiveMarketService shutdown complete")

    def health_check(self) -> bool:
        pass

def main():
    parser = argparse.ArgumentParser(description="Live Market Data Service")
    parser.add_argument(
        'command', 
        choices=['run', 'health'],
        help="Command to execute"
    )
    parser.add_argument(
        '--log-level', default='INFO',
        choices=['DEBUG','INFO','WARNING','ERROR'],
        help='Set logging level'
    )
    parser.add_argument(
        '--sleep-interval', type=int, default=None,
        help="Override sleep interval in seconds"
    )

    args = parser.parse_args()

    try:
        service = LiveMarketService(sleep_override=args.sleep_interval)

        if args.command == 'run':
            service.logger.info("Starting live market service...")
            if args.sleep_interval:
                service.logger.info(f"Using fixed sleep interval: {args.sleep_interval}")
            service.run()
            return 0
        elif args.command == 'health':
            if service.health_check():
                service.logger.info("Not yet implemented")
                return 0

    except KeyboardInterrupt:
        print("Service interrupted by user")
        return 0
    except Exception as e:
        print(f"Service failed to start: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

