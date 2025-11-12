"""Daemon service for processing bad tickers from Redis to SQLite."""

import signal
import time

from infrastructure.logging.logger import get_logger
from system.algo_trader.redis.queue_broker import QueueBroker
from system.algo_trader.sqlite.bad_ticker_client import BadTickerClient

BAD_TICKER_QUEUE_NAME = "bad_ticker_queue"
POLL_INTERVAL = 2


class BadTickerDaemon:
    """Daemon that processes bad ticker queue and writes to SQLite."""

    def __init__(self) -> None:
        """Initialize bad ticker daemon."""
        self.logger = get_logger(self.__class__.__name__)
        self.running = False
        self.queue_broker = QueueBroker(namespace="queue")
        self.sqlite_client = BadTickerClient()
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame) -> None:
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        self.running = False

    def _process_queue(self) -> None:
        queue_size = self.queue_broker.get_queue_size(BAD_TICKER_QUEUE_NAME)
        if queue_size == 0:
            return

        self.logger.info(f"Processing queue '{BAD_TICKER_QUEUE_NAME}' ({queue_size} items pending)")

        processed_count = 0
        failed_count = 0

        while self.running:
            item_id = self.queue_broker.dequeue(BAD_TICKER_QUEUE_NAME)
            if not item_id:
                break

            data = self.queue_broker.get_data(BAD_TICKER_QUEUE_NAME, item_id)
            if not data:
                self.logger.error(f"No data found for {item_id}, skipping")
                failed_count += 1
                continue

            ticker = data.get("ticker")
            timestamp = data.get("timestamp")
            reason = data.get("reason")

            if not ticker or not timestamp or not reason:
                self.logger.error(
                    f"Invalid data structure for {item_id} "
                    f"(ticker={ticker}, timestamp={timestamp}, reason={reason})"
                )
                self.queue_broker.delete_data(BAD_TICKER_QUEUE_NAME, item_id)
                failed_count += 1
                continue

            try:
                success = self.sqlite_client.log_bad_ticker(ticker, timestamp, reason)

                if success:
                    self.logger.info(f"Successfully logged bad ticker: {ticker} - {reason}")
                    processed_count += 1
                else:
                    self.logger.error(f"Failed to log bad ticker {ticker} to SQLite")
                    failed_count += 1

                self.queue_broker.delete_data(BAD_TICKER_QUEUE_NAME, item_id)

            except Exception as e:
                self.logger.error(f"Error processing {item_id}: {e}")
                self.queue_broker.delete_data(BAD_TICKER_QUEUE_NAME, item_id)
                failed_count += 1

        self.logger.info(
            f"Queue '{BAD_TICKER_QUEUE_NAME}' processing complete: "
            f"{processed_count} successful, {failed_count} failed"
        )

    def run(self) -> None:
        """Run the daemon main loop."""
        self.logger.info("Starting Bad Ticker Daemon...")
        self.logger.info(f"Monitoring queue: {BAD_TICKER_QUEUE_NAME}")

        self.running = True

        while self.running:
            try:
                self._process_queue()
                if self.running:
                    time.sleep(POLL_INTERVAL)
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                if self.running:
                    time.sleep(POLL_INTERVAL)

        self.logger.info("Shutdown complete")
        self._cleanup()

    def _cleanup(self) -> None:
        self.logger.info("Closing SQLite connection...")
        try:
            self.sqlite_client.close()
            self.logger.info("Closed SQLite client")
        except Exception as e:
            self.logger.warning(f"Error closing SQLite client: {e}")


def main() -> None:
    """Main entry point for bad ticker daemon."""
    daemon = BadTickerDaemon()
    daemon.run()


if __name__ == "__main__":
    main()
