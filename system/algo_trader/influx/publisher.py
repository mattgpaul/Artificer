"""InfluxDB Publisher service.

Publishes market data from Redis queues to InfluxDB databases.
Monitors configured queues and processes items in batches.
"""

import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from infrastructure.influxdb.influxdb import BatchWriteConfig
from infrastructure.logging.logger import get_logger
from system.algo_trader.influx.market_data_influx import MarketDataInflux
from system.algo_trader.redis.queue_broker import QueueBroker

# Hard-coded database names - each queue type uses its own database for isolation
OHLCV_DATABASE = "algo-trader-ohlcv"
FUNDAMENTALS_DATABASE = "algo-trader-fundamentals"
TRADING_JOURNAL_DATABASE = "algo-trader-trading-journal"

# Hard-coded batch sizes - protected constants to prevent configuration errors
#
# CRITICAL: These constants are PROTECTED and MUST NOT be modified without explicit user approval.
# ALWAYS ask the user before changing any of these values.
#
# OHLCV_BATCH_SIZE is read-only and MUST NOT be modified without code review
OHLCV_BATCH_SIZE = 300_000  # Protected constant - do not modify
FUNDAMENTALS_BATCH_SIZE = 50_000  # Protected constant - ask user before modifying
TRADING_JOURNAL_BATCH_SIZE = 50_000  # Protected constant - ask user before modifying
BACKTEST_BATCH_SIZE = 50_000  # Protected constant - ask user before modifying


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
        self.config = self._load_config(config_path)
        self.queue_broker = QueueBroker(namespace=self._get_namespace())
        self.influx_clients: dict[str, MarketDataInflux] = {}
        self._init_influx_clients()

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _get_namespace(self) -> str:
        if self.config and "queues" in self.config and len(self.config["queues"]) > 0:
            return self.config["queues"][0].get("namespace", "queue")
        return "queue"

    def _load_config(self, config_path: str) -> dict[str, Any]:
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                self.logger.error(f"Config file not found: {config_path}")
                sys.exit(1)

            with open(config_file) as f:
                config = yaml.safe_load(f)

            self.logger.info(f"Loaded config from {config_path}")
            return config

        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            sys.exit(1)

    def _init_influx_clients(self) -> None:
        """Initialize InfluxDB clients for each queue with hard-coded databases and batch sizes.

        Maps queue names to their respective databases and batch sizes:
        - ohlcv_queue -> algo-trader-ohlcv (300k batch size, protected)
        - fundamentals_queue -> algo-trader-fundamentals (50k batch size)
        - trading_journal_queue -> algo-trader-trading-journal (50k batch size)
        """
        # Map queue names to their databases and batch sizes
        queue_database_map = {
            "ohlcv_queue": (OHLCV_DATABASE, OHLCV_BATCH_SIZE),
            "fundamentals_queue": (FUNDAMENTALS_DATABASE, FUNDAMENTALS_BATCH_SIZE),
            "trading_journal_queue": (TRADING_JOURNAL_DATABASE, TRADING_JOURNAL_BATCH_SIZE),
            "backtest_trades_queue": (TRADING_JOURNAL_DATABASE, BACKTEST_BATCH_SIZE),
            "backtest_metrics_queue": (TRADING_JOURNAL_DATABASE, BACKTEST_BATCH_SIZE),
        }

        for queue_config in self.config.get("queues", []):
            queue_name = queue_config["name"]

            # Get database and batch size from hard-coded mapping
            if queue_name not in queue_database_map:
                self.logger.error(
                    f"Unknown queue '{queue_name}'. Must be one of: "
                    f"{', '.join(queue_database_map.keys())}"
                )
                sys.exit(1)

            database, batch_size = queue_database_map[queue_name]

            # Validate OHLCV batch size is using the protected constant
            if queue_name == "ohlcv_queue" and batch_size != OHLCV_BATCH_SIZE:
                self.logger.error(
                    f"OHLCV batch size must be {OHLCV_BATCH_SIZE}. "
                    f"Attempted to use {batch_size}. This is a protected constant."
                )
                sys.exit(1)

            # Create write config with hard-coded batch size and other params from YAML
            write_config = BatchWriteConfig(
                batch_size=batch_size,  # Hard-coded, not from config
                flush_interval=queue_config.get("flush_interval", 10000),
                jitter_interval=queue_config.get("jitter_interval", 2000),
                retry_interval=queue_config.get("retry_interval", 15000),
                max_retries=queue_config.get("max_retries", 5),
                max_retry_delay=queue_config.get("max_retry_delay", 30000),
                exponential_base=queue_config.get("exponential_base", 2),
            )

            self.influx_clients[queue_name] = MarketDataInflux(
                database=database, write_config=write_config
            )

            self.logger.info(
                f"Initialized InfluxDB client for queue '{queue_name}' -> "
                f"database '{database}' (batch_size={write_config.batch_size})"
            )

    def _signal_handler(self, signum, frame) -> None:
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        self.running = False

    def _process_queue(self, queue_config: dict[str, Any]) -> None:
        queue_name = queue_config["name"]
        table_name = queue_config["table"]
        influx_client = self.influx_clients[queue_name]

        queue_size = self.queue_broker.get_queue_size(queue_name)
        if queue_size == 0:
            return

        self.logger.info(f"Processing queue '{queue_name}' ({queue_size} items pending)")

        processed_count = 0
        failed_count = 0

        while self.running:
            item_id = self.queue_broker.dequeue(queue_name)
            if not item_id:
                break

            data = self.queue_broker.get_data(queue_name, item_id)
            if not data:
                self.logger.error(f"No data found for {item_id}, skipping")
                failed_count += 1
                continue

            ticker = data.get("ticker")
            time_series_data = data.get("candles") or data.get("data")

            if not ticker or not time_series_data:
                self.logger.error(
                    f"Invalid data structure for {item_id} (ticker={ticker}, "
                    f"data={'present' if time_series_data else 'missing'})"
                )
                self.queue_broker.delete_data(queue_name, item_id)
                failed_count += 1
                continue

            dynamic_table_name = table_name
            tag_columns = ["ticker"]

            if queue_name.startswith("backtest_"):
                strategy_name = data.get("strategy_name")
                if strategy_name:
                    if queue_name == "backtest_trades_queue":
                        dynamic_table_name = strategy_name
                    elif queue_name == "backtest_metrics_queue":
                        dynamic_table_name = f"{strategy_name}_summary"

                backtest_id = data.get("backtest_id")
                backtest_hash = data.get("backtest_hash")

                data_length = len(time_series_data.get("datetime", []))
                if data_length == 0:
                    self.logger.warning(f"Empty datetime array in {item_id}, skipping")
                    self.queue_broker.delete_data(queue_name, item_id)
                    failed_count += 1
                    continue

                if backtest_id:
                    if "backtest_id" not in time_series_data:
                        time_series_data["backtest_id"] = [backtest_id] * data_length
                    tag_columns.append("backtest_id")
                if backtest_hash:
                    if "backtest_hash" not in time_series_data:
                        time_series_data["backtest_hash"] = [backtest_hash] * data_length
                    tag_columns.append("backtest_hash")

                if strategy_name:
                    if "strategy" not in time_series_data:
                        time_series_data["strategy"] = [strategy_name] * data_length
                    tag_columns.append("strategy")

            try:
                success = influx_client.write_sync(
                    data=time_series_data, ticker=ticker, table=dynamic_table_name, tag_columns=tag_columns
                )

                if success:
                    data_count = (
                        len(time_series_data)
                        if isinstance(time_series_data, list)
                        else len(time_series_data.get("datetime", []))
                    )
                    self.logger.info(f"Successfully wrote {data_count} records for {ticker}")
                    processed_count += 1
                else:
                    self.logger.error(f"Failed to write data for {ticker} to InfluxDB")
                    failed_count += 1

                self.queue_broker.delete_data(queue_name, item_id)

            except Exception as e:
                self.logger.error(f"Error processing {item_id}: {e}")
                self.queue_broker.delete_data(queue_name, item_id)
                failed_count += 1

        self.logger.info(
            f"Queue '{queue_name}' processing complete: "
            f"{processed_count} successful, {failed_count} failed"
        )

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
                    self._process_queue(queue_config)

                if self.running:
                    time.sleep(poll_interval)

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                if self.running:
                    time.sleep(poll_interval)

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

    publisher = InfluxPublisher(config_path)
    publisher.run()


if __name__ == "__main__":
    main()
