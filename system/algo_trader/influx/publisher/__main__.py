"""Entry point for running the InfluxDB publisher as a module."""

import os
import sys

from system.algo_trader.influx.publisher.publisher import InfluxPublisher

if __name__ == "__main__":
    # Get config path from environment or use default
    config_path = os.getenv(
        "PUBLISHER_CONFIG_PATH", "/workspace/system/algo_trader/influx/publisher_config.yaml"
    )

    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    # Create and run publisher
    publisher = InfluxPublisher(config_path)
    publisher.run()
