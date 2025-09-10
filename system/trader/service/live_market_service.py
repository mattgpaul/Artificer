import sys
import argparse
import time
from datetime import datetime, timezone

from component.software.finance.schema import MarketHours
from system.trader.service.market_base import MarketBase, MarketHoursType

class LiveMarketService(MarketBase):
    def __init__(self, sleep_override=None):
        super().__init__(sleep_override)

    def _get_sleep_interval(self) -> int:
        self.logger.info("Getting sleep interval")
        # Check if there is an override
        if self.sleep_override is not None:
            self.logger.debug(f"Using sleep override: {self.sleep_override} seconds")
            return self.sleep_override

        todays_hours = self.market_broker.get_market_hours()
        market_open = self._check_market_open(todays_hours)
        if not market_open:
            sleep_interval = 60*60  # 1 hour intervals outside market hours
            return sleep_interval
        todays_hours = MarketHours(**todays_hours)
        self.logger.debug(f"Todays hours: {todays_hours}")
        current_market = self._check_market_hours(todays_hours)
        
        if current_market == MarketHoursType.PREMARKET:
            sleep_interval = 60*5  # 5min intervals
            self.logger.info("5min intervals")
        elif current_market == MarketHoursType.STANDARD:
            sleep_interval = 1  # 1 second intervals
            self.logger.info("1s intervals")
        else:
            sleep_interval = 60*60  # 1 hour intervals
            self.logger.info("1hr intervals")

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

