"""Fundamentals daemon for processing Redis queue and writing to SQLite.

This daemon monitors the fundamentals_static_queue Redis queue and writes
static fundamentals data to SQLite database.
"""

import signal
import time

from infrastructure.logging.logger import get_logger
from system.algo_trader.redis.queue_broker import QueueBroker
from system.algo_trader.sqlite.fundamentals_client import FundamentalsClient

FUNDAMENTALS_STATIC_QUEUE_NAME = "fundamentals_static_queue"
POLL_INTERVAL = 2


class FundamentalsDaemon:
    """Daemon for processing fundamentals static data from Redis to SQLite.

    Continuously monitors Redis queue for fundamentals static data and writes
    it to SQLite database. Handles graceful shutdown on SIGTERM/SIGINT.
    """

    def __init__(self) -> None:
        """Initialize FundamentalsDaemon with queue broker and SQLite client."""
        self.logger = get_logger(self.__class__.__name__)
        self.running = False
        self.queue_broker = QueueBroker(namespace="queue")
        self.sqlite_client = FundamentalsClient()
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame) -> None:
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        self.running = False

    def _process_queue(self) -> None:
        queue_size = self.queue_broker.get_queue_size(FUNDAMENTALS_STATIC_QUEUE_NAME)
        if queue_size == 0:
            return

        self.logger.info(
            f"Processing queue '{FUNDAMENTALS_STATIC_QUEUE_NAME}' ({queue_size} items pending)"
        )

        processed_count = 0
        failed_count = 0

        while self.running:
            item_id = self.queue_broker.dequeue(FUNDAMENTALS_STATIC_QUEUE_NAME)
            if not item_id:
                break

            try:
                data = self.queue_broker.get_data(FUNDAMENTALS_STATIC_QUEUE_NAME, item_id)
            except Exception as e:
                self.logger.error(f"Error retrieving data for {item_id}: {e}")
                self.queue_broker.delete_data(FUNDAMENTALS_STATIC_QUEUE_NAME, item_id)
                failed_count += 1
                continue

            if not data:
                self.logger.error(f"No data found for {item_id}, skipping")
                failed_count += 1
                continue

            ticker = data.get("ticker")

            if not ticker:
                self.logger.error(f"Invalid data structure for {item_id} (ticker={ticker})")
                self.queue_broker.delete_data(FUNDAMENTALS_STATIC_QUEUE_NAME, item_id)
                failed_count += 1
                continue

            try:
                success = self.sqlite_client.upsert_fundamentals(data)

                if success:
                    self.logger.info(f"Successfully upserted fundamentals for ticker: {ticker}")
                    processed_count += 1
                else:
                    self.logger.error(f"Failed to upsert fundamentals for {ticker} to SQLite")
                    failed_count += 1

                self.queue_broker.delete_data(FUNDAMENTALS_STATIC_QUEUE_NAME, item_id)

            except Exception as e:
                self.logger.error(f"Error processing {item_id}: {e}")
                self.queue_broker.delete_data(FUNDAMENTALS_STATIC_QUEUE_NAME, item_id)
                failed_count += 1

        self.logger.info(
            f"Queue '{FUNDAMENTALS_STATIC_QUEUE_NAME}' processing complete: "
            f"{processed_count} successful, {failed_count} failed"
        )

    def run(self) -> None:
        """Run the daemon main loop.

        Continuously polls Redis queue for fundamentals static data and processes
        items until shutdown signal is received.
        """
        self.logger.info("Starting Fundamentals Daemon...")
        self.logger.info(f"Monitoring queue: {FUNDAMENTALS_STATIC_QUEUE_NAME}")

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
    """Entry point for fundamentals daemon."""
    daemon = FundamentalsDaemon()
    daemon.run()


if __name__ == "__main__":
    main()
