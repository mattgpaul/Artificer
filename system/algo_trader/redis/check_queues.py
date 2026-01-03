"""Utility script to check Redis queue status.

This script provides diagnostics for Redis queues, particularly useful
for debugging why data might not be appearing in MySQL/InfluxDB.
"""

import sys
from typing import Any

from infrastructure.logging.logger import get_logger
from system.algo_trader.redis.queue_broker import QueueBroker

# Queue names to check
FUNDAMENTALS_STATIC_QUEUE = "fundamentals_static_queue"
FUNDAMENTALS_QUEUE = "fundamentals_queue"
OHLCV_QUEUE = "ohlcv_queue"
BAD_TICKER_QUEUE = "bad_ticker_queue"


def check_queue_status(queue_broker: QueueBroker, queue_name: str) -> dict[str, Any]:
    """Check status of a specific queue.

    Args:
        queue_broker: QueueBroker instance.
        queue_name: Name of the queue to check.

    Returns:
        Dictionary with queue status information.
    """
    size = queue_broker.get_queue_size(queue_name)
    peek_items = queue_broker.peek_queue(queue_name, count=10)

    # Try to get sample data for first few items
    sample_data = []
    for item_id in peek_items[:3]:
        data = queue_broker.get_data(queue_name, item_id)
        if data:
            # Extract key info without full data dump
            sample_info = {"item_id": item_id}
            if isinstance(data, dict):
                if "ticker" in data:
                    sample_info["ticker"] = data["ticker"]
                sample_info["keys"] = list(data.keys())[:5]  # First 5 keys
            sample_data.append(sample_info)

    return {
        "size": size,
        "sample_items": peek_items[:10],
        "sample_data": sample_data,
    }


def main() -> int:
    """Main entry point for queue status checker."""
    logger = get_logger("QueueStatusChecker")

    try:
        queue_broker = QueueBroker(namespace="queue")
        logger.info("Connected to Redis")

        queues_to_check = [
            FUNDAMENTALS_STATIC_QUEUE,
            FUNDAMENTALS_QUEUE,
            OHLCV_QUEUE,
            BAD_TICKER_QUEUE,
        ]

        print("\n" + "=" * 70)
        print("Redis Queue Status Report")
        print("=" * 70 + "\n")

        total_pending = 0

        for queue_name in queues_to_check:
            status = check_queue_status(queue_broker, queue_name)
            total_pending += status["size"]

            print(f"Queue: {queue_name}")
            print(f"  Size: {status['size']} items pending")
            if status["size"] > 0:
                print(f"  Sample items: {', '.join(status['sample_items'][:5])}")
                if status["sample_data"]:
                    print("  Sample data:")
                    for sample in status["sample_data"]:
                        ticker_info = (
                            f" (ticker: {sample.get('ticker', 'N/A')})"
                            if "ticker" in sample
                            else ""
                        )
                        print(f"    - {sample['item_id']}{ticker_info}")
            else:
                print("  Status: Empty")
            print()

        print("=" * 70)
        print(f"Total items pending across all queues: {total_pending}")
        print("=" * 70)

        if total_pending > 0:
            print("\n⚠️  WARNING: There are items pending in Redis queues.")
            print("   Make sure the following services are running:")
            print("   - mysql-daemon (processes fundamentals_static_queue)")
            print("   - influx-publisher (processes fundamentals_queue, ohlcv_queue)")
            print()

        # Check for fundamentals queues specifically
        fundamentals_static_size = check_queue_status(queue_broker, FUNDAMENTALS_STATIC_QUEUE)[
            "size"
        ]
        if fundamentals_static_size > 0:
            print(f"⚠️  {fundamentals_static_size} items in '{FUNDAMENTALS_STATIC_QUEUE}'")
            print("   These should be processed by mysql-daemon and written to MySQL.")
            print("   Check mysql-daemon logs if items aren't being processed.\n")

        fundamentals_size = check_queue_status(queue_broker, FUNDAMENTALS_QUEUE)["size"]
        if fundamentals_size > 0:
            print(f"⚠️  {fundamentals_size} items in '{FUNDAMENTALS_QUEUE}'")
            print("   These should be processed by influx-publisher and written to InfluxDB.")
            print("   Check influx-publisher logs if items aren't being processed.\n")

        return 0

    except Exception as e:
        logger.error(f"Error checking queue status: {e}")
        print(f"\n❌ Error: {e}")
        print("\nMake sure Redis is running and accessible.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
