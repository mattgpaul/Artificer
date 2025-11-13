"""MySQL daemon for processing multiple Redis queues.

This daemon monitors multiple Redis queues and writes data to MySQL database.
Currently handles bad_ticker_queue and fundamentals_static_queue.
"""

import signal
import time

from infrastructure.logging.logger import get_logger
from system.algo_trader.mysql.bad_ticker_client import BadTickerClient
from system.algo_trader.mysql.fundamentals_client import FundamentalsClient
from system.algo_trader.redis.queue_broker import QueueBroker

BAD_TICKER_QUEUE_NAME = "bad_ticker_queue"
FUNDAMENTALS_STATIC_QUEUE_NAME = "fundamentals_static_queue"
POLL_INTERVAL = 2


class MySQLDaemon:
    """Daemon that processes multiple MySQL queues.

    Continuously monitors Redis queues for data and writes to MySQL database.
    Handles graceful shutdown on SIGTERM/SIGINT signals.
    """

    def __init__(self) -> None:
        """Initialize MySQL daemon with queue broker and MySQL clients."""
        self.logger = get_logger(self.__class__.__name__)
        self.running = False
        self.queue_broker = QueueBroker(namespace="queue")

        # Initialize clients for each queue type
        self.bad_ticker_client = BadTickerClient()
        self.fundamentals_client = FundamentalsClient()

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals gracefully."""
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        self.running = False

    def _process_bad_ticker_queue(self) -> None:
        """Process bad ticker queue."""
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

            try:
                data = self.queue_broker.get_data(BAD_TICKER_QUEUE_NAME, item_id)
            except Exception as e:
                self.logger.error(f"Error retrieving data for {item_id}: {e}")
                self.queue_broker.delete_data(BAD_TICKER_QUEUE_NAME, item_id)
                failed_count += 1
                continue

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
                success = self.bad_ticker_client.log_bad_ticker(ticker, timestamp, reason)

                if success:
                    self.logger.info(f"Successfully logged bad ticker: {ticker} - {reason}")
                    processed_count += 1
                else:
                    self.logger.error(f"Failed to log bad ticker {ticker} to MySQL")
                    failed_count += 1

                self.queue_broker.delete_data(BAD_TICKER_QUEUE_NAME, item_id)

            except Exception as e:
                self.logger.error(f"Error processing {item_id}: {e}")
                self.queue_broker.delete_data(BAD_TICKER_QUEUE_NAME, item_id)
                failed_count += 1

        if processed_count > 0 or failed_count > 0:
            self.logger.info(
                f"Queue '{BAD_TICKER_QUEUE_NAME}' processing complete: "
                f"{processed_count} successful, {failed_count} failed"
            )

    def _process_fundamentals_queue(self) -> None:
        """Process fundamentals static data queue."""
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
                success = self.fundamentals_client.upsert_fundamentals(data)

                if success:
                    self.logger.info(f"Successfully upserted fundamentals for ticker: {ticker}")
                    processed_count += 1
                else:
                    self.logger.error(f"Failed to upsert fundamentals for {ticker} to MySQL")
                    failed_count += 1

                self.queue_broker.delete_data(FUNDAMENTALS_STATIC_QUEUE_NAME, item_id)

            except Exception as e:
                self.logger.error(f"Error processing {item_id}: {e}")
                self.queue_broker.delete_data(FUNDAMENTALS_STATIC_QUEUE_NAME, item_id)
                failed_count += 1

        if processed_count > 0 or failed_count > 0:
            self.logger.info(
                f"Queue '{FUNDAMENTALS_STATIC_QUEUE_NAME}' processing complete: "
                f"{processed_count} successful, {failed_count} failed"
            )

    def run(self) -> None:
        """Run the daemon main loop.

        Continuously polls Redis queues for data and processes items until
        shutdown signal is received.
        """
        self.logger.info("Starting MySQL Daemon...")
        self.logger.info(
            f"Monitoring queues: {BAD_TICKER_QUEUE_NAME}, {FUNDAMENTALS_STATIC_QUEUE_NAME}"
        )

        self.running = True

        while self.running:
            try:
                # Process each queue in sequence
                self._process_bad_ticker_queue()
                self._process_fundamentals_queue()

                if self.running:
                    time.sleep(POLL_INTERVAL)
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                if self.running:
                    time.sleep(POLL_INTERVAL)

        self.logger.info("Shutdown complete")
        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up all MySQL connections."""
        self.logger.info("Closing MySQL connections...")
        try:
            self.bad_ticker_client.close()
            self.logger.info("Closed BadTickerClient")
        except Exception as e:
            self.logger.warning(f"Error closing BadTickerClient: {e}")

        try:
            self.fundamentals_client.close()
            self.logger.info("Closed FundamentalsClient")
        except Exception as e:
            self.logger.warning(f"Error closing FundamentalsClient: {e}")


def main() -> None:
    """Main entry point for MySQL daemon."""
    daemon = MySQLDaemon()
    daemon.run()


if __name__ == "__main__":
    main()
