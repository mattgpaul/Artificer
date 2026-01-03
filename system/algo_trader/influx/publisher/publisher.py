"""InfluxDB Publisher service.

Publishes market data from Redis queues to InfluxDB databases.
Monitors configured queues and processes items in batches.
"""

import os
import signal
import time

from infrastructure.logging.logger import get_logger
from system.algo_trader.influx.publisher.config import (
    get_namespace,
    init_influx_clients,
    load_config,
)
from system.algo_trader.influx.publisher.queue_processor import process_queue
from system.algo_trader.redis.queue_broker import QueueBroker

SLEEP_CHECK_INTERVAL = 0.1  # Check running flag every 100ms during sleep


class InfluxPublisher:
    """Publisher service for writing market data to InfluxDB.

    Reads data from Redis queues and writes to InfluxDB tables based on
    configuration. Supports multiple queues with independent batch configurations.

    Args:
        config_path: Path to YAML configuration file.
    """

    def __init__(self, config_path: str) -> None:
        """Initialize InfluxDB publisher with configuration.

        Args:
            config_path: Path to YAML configuration file.
        """
        self.logger = get_logger(self.__class__.__name__)
        self.running = False
        self.config = load_config(config_path, self.logger)
        namespace = get_namespace(self.config)
        self.queue_broker = QueueBroker(namespace=namespace)
        self.influx_clients = init_influx_clients(self.config, self.logger)

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame) -> None:
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        self.running = False

    def _interruptible_sleep(self, duration: float) -> None:
        """Sleep in small increments, checking running flag to allow quick shutdown.

        Args:
            duration: Total sleep duration in seconds.
        """
        elapsed = 0.0
        while elapsed < duration and self.running:
            sleep_time = min(SLEEP_CHECK_INTERVAL, duration - elapsed)
            time.sleep(sleep_time)
            elapsed += sleep_time

    def run(self) -> None:
        """Run the publisher daemon.

        Continuously monitors configured queues and processes items.
        Handles graceful shutdown on SIGTERM/SIGINT signals.
        """
        self.logger.info("Starting InfluxDB Publisher daemon...")
        self.logger.info(f"Monitoring {len(self.config.get('queues', []))} queues")

        for queue_config in self.config.get("queues", []):
            self.logger.info(f"  - {queue_config['name']} -> table '{queue_config['table']}'")

        self.running = True

        poll_interval = self.config.get("queues", [{}])[0].get("poll_interval", 2)

        while self.running:
            try:
                for queue_config in self.config.get("queues", []):
                    if not self.running:
                        break
                    process_queue(
                        queue_config,
                        self.queue_broker,
                        self.influx_clients[queue_config["name"]],
                        lambda: self.running,
                        self.logger,
                    )

                if self.running:
                    self._interruptible_sleep(poll_interval)

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                if self.running:
                    self._interruptible_sleep(poll_interval)

        self.logger.info("Shutdown complete")
        self._cleanup()

    def _cleanup(self) -> None:
        self.logger.info("Closing InfluxDB connections...")
        for queue_name, client in self.influx_clients.items():
            try:
                client.close()
                self.logger.info(f"Closed InfluxDB client for '{queue_name}'")
            except Exception as e:
                self.logger.warning(f"Error closing client for '{queue_name}': {e}")


def main() -> None:
    """Main entry point for InfluxDB publisher service.

    Loads configuration from environment variable or default path,
    initializes publisher, and runs the daemon.
    """
    config_path = os.getenv(
        "PUBLISHER_CONFIG",
        "/app/system/algo_trader/influx/publisher_config.yaml",
    )
    # Adjust path if running from within publisher/ directory
    if not os.path.exists(config_path) and os.path.exists("../publisher_config.yaml"):
        config_path = "../publisher_config.yaml"

    publisher = InfluxPublisher(config_path)
    publisher.run()


if __name__ == "__main__":
    main()
