"""Configuration loading for InfluxDB publisher.

This module provides functionality to load and parse publisher configuration
files and initialize InfluxDB clients with appropriate batch write settings.
"""

import sys
from pathlib import Path
from typing import Any

import yaml

from infrastructure.influxdb.influxdb import BatchWriteConfig
from infrastructure.logging.logger import get_logger
from system.algo_trader.influx.market_data_influx import MarketDataInflux

OHLCV_DATABASE = "ohlcv"
FUNDAMENTALS_DATABASE = "algo-trader-fundamentals"
TRADING_JOURNAL_DATABASE = "algo-trader-trading-journal"

OHLCV_BATCH_SIZE = 300_000
FUNDAMENTALS_BATCH_SIZE = 50_000
TRADING_JOURNAL_BATCH_SIZE = 50_000
BACKTEST_BATCH_SIZE = 50_000


def load_config(config_path: str, logger=None) -> dict[str, Any]:
    """Load publisher configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file.
        logger: Optional logger instance. If not provided, creates a new logger.

    Returns:
        Dictionary containing parsed configuration.

    Exits:
        sys.exit(1): If config file is not found or cannot be loaded.
    """
    logger = logger or get_logger("ConfigLoader")
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            logger.error(f"Config file not found: {config_path}")
            sys.exit(1)

        with open(config_file) as f:
            config = yaml.safe_load(f)

        logger.info(f"Loaded config from {config_path}")
        return config

    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)


def get_namespace(config: dict[str, Any]) -> str:
    """Extract namespace from configuration.

    Args:
        config: Configuration dictionary.

    Returns:
        Namespace string from first queue config, or "queue" as default.
    """
    if config and "queues" in config and len(config["queues"]) > 0:
        return config["queues"][0].get("namespace", "queue")
    return "queue"


def init_influx_clients(config: dict[str, Any], logger=None) -> dict[str, MarketDataInflux]:
    """Initialize InfluxDB clients for configured queues.

    Creates MarketDataInflux clients for each queue specified in the config,
    mapping queues to appropriate databases and batch sizes.

    Args:
        config: Configuration dictionary containing queue definitions.
        logger: Optional logger instance. If not provided, creates a new logger.

    Returns:
        Dictionary mapping queue names to MarketDataInflux client instances.

    Exits:
        sys.exit(1): If unknown queue name is encountered or OHLCV batch size is invalid.
    """
    logger = logger or get_logger("InfluxClientInit")
    queue_database_map = {
        "ohlcv_queue": (OHLCV_DATABASE, OHLCV_BATCH_SIZE),
        "fundamentals_queue": (FUNDAMENTALS_DATABASE, FUNDAMENTALS_BATCH_SIZE),
        "trading_journal_queue": (TRADING_JOURNAL_DATABASE, TRADING_JOURNAL_BATCH_SIZE),
        "backtest_trades_queue": (TRADING_JOURNAL_DATABASE, BACKTEST_BATCH_SIZE),
        "backtest_metrics_queue": (TRADING_JOURNAL_DATABASE, BACKTEST_BATCH_SIZE),
    }

    influx_clients: dict[str, MarketDataInflux] = {}

    for queue_config in config.get("queues", []):
        queue_name = queue_config["name"]

        if queue_name not in queue_database_map:
            logger.error(
                f"Unknown queue '{queue_name}'. Must be one of: "
                f"{', '.join(queue_database_map.keys())}"
            )
            sys.exit(1)

        database, batch_size = queue_database_map[queue_name]

        if queue_name == "ohlcv_queue" and batch_size != OHLCV_BATCH_SIZE:
            logger.error(
                f"OHLCV batch size must be {OHLCV_BATCH_SIZE}. "
                f"Attempted to use {batch_size}. This is a protected constant."
            )
            sys.exit(1)

        write_config = BatchWriteConfig(
            batch_size=batch_size,
            flush_interval=queue_config.get("flush_interval", 10000),
            jitter_interval=queue_config.get("jitter_interval", 2000),
            retry_interval=queue_config.get("retry_interval", 15000),
            max_retries=queue_config.get("max_retries", 5),
            max_retry_delay=queue_config.get("max_retry_delay", 30000),
            exponential_base=queue_config.get("exponential_base", 2),
        )

        influx_clients[queue_name] = MarketDataInflux(database=database, write_config=write_config)

        logger.info(
            f"Initialized InfluxDB client for queue '{queue_name}' -> "
            f"database '{database}' (batch_size={write_config.batch_size})"
        )

    return influx_clients
