"""Queue processor for InfluxDB publisher.

This module provides functionality to process Redis queues and write data
to InfluxDB, handling various data formats and error conditions.
"""

from typing import Any

from infrastructure.logging.logger import get_logger
from system.algo_trader.influx.market_data_influx import MarketDataInflux
from system.algo_trader.redis.queue_broker import QueueBroker


def process_queue(
    queue_config: dict[str, Any],
    queue_broker: QueueBroker,
    influx_client: MarketDataInflux,
    running: bool,
    logger=None,
) -> tuple[int, int]:
    """Process items from Redis queue and write to InfluxDB.

    Dequeues items from Redis queue, validates data structure, and writes
    to InfluxDB. Handles various data formats (candles, data) and error conditions.

    Args:
        queue_config: Dictionary containing queue configuration with 'name' and 'table'.
        queue_broker: QueueBroker instance for Redis operations.
        influx_client: MarketDataInflux client for writing to InfluxDB.
        running: Boolean flag indicating if processing should continue.
        logger: Optional logger instance. If not provided, creates a new logger.

    Returns:
        Tuple of (processed_count, failed_count) indicating processing results.
    """
    logger = logger or get_logger("QueueProcessor")
    queue_name = queue_config["name"]
    table_name = queue_config["table"]

    queue_size = queue_broker.get_queue_size(queue_name)
    if queue_size == 0:
        return 0, 0

    logger.info(f"Processing queue '{queue_name}' ({queue_size} items pending)")

    processed_count = 0
    failed_count = 0

    while running:
        item_id = queue_broker.dequeue(queue_name)
        if not item_id:
            break

        data = queue_broker.get_data(queue_name, item_id)
        if not data:
            logger.error(f"No data found for {item_id}, skipping")
            failed_count += 1
            continue

        ticker = data.get("ticker")
        time_series_data = data.get("candles") or data.get("data")

        # Log data processing at debug level
        logger.debug(f"Processing {item_id}: ticker={ticker}")

        if not ticker or not time_series_data:
            logger.error(
                f"Invalid data structure for {item_id} (ticker={ticker}, "
                f"data={'present' if time_series_data else 'missing'})"
            )
            queue_broker.delete_data(queue_name, item_id)
            failed_count += 1
            continue

        # Check for empty candles/data for ohlcv_queue and fundamentals_queue
        if queue_name in ("ohlcv_queue", "fundamentals_queue"):
            if isinstance(time_series_data, list):
                if len(time_series_data) == 0:
                    logger.warning(
                        f"Empty {queue_name} data for {item_id} (ticker: {ticker}), skipping"
                    )
                    queue_broker.delete_data(queue_name, item_id)
                    failed_count += 1
                    continue
            elif isinstance(time_series_data, dict):
                # Check if datetime array exists and is empty
                datetime_array = time_series_data.get("datetime", [])
                if not datetime_array or len(datetime_array) == 0:
                    logger.warning(
                        f"Empty datetime array in {queue_name} for {item_id} "
                        f"(ticker: {ticker}), skipping"
                    )
                    queue_broker.delete_data(queue_name, item_id)
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
                logger.warning(f"Empty datetime array in {item_id}, skipping")
                queue_broker.delete_data(queue_name, item_id)
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

        # Validate data before writing
        if isinstance(time_series_data, dict):
            # Validate datetime array exists and has correct length
            datetime_array = time_series_data.get("datetime", [])
            if not datetime_array:
                logger.error(f"No datetime array found in {item_id}")
                queue_broker.delete_data(queue_name, item_id)
                failed_count += 1
                continue

            data_length = len(datetime_array)

            # Validate tag columns don't contain NaN values
            # Note: ticker is handled separately by write(), so we skip it here
            for tag_col in tag_columns:
                if tag_col == "ticker":
                    continue  # Ticker is handled separately by write()

                if tag_col in time_series_data:
                    tag_values = time_series_data[tag_col]
                    if isinstance(tag_values, list):
                        # Check for None or invalid values in tag columns
                        # InfluxDB line protocol requires tags to have non-empty values
                        if any(v is None or v == "" for v in tag_values):
                            logger.warning(
                                f"Found None/empty values in tag column '{tag_col}' for {item_id}, "
                                "replacing with 'unknown' placeholder"
                            )
                            time_series_data[tag_col] = [
                                "unknown" if (v is None or v == "") else str(v)
                                for v in tag_values
                            ]
                        else:
                            # Ensure all tag values are strings
                            time_series_data[tag_col] = [
                                str(v) for v in time_series_data[tag_col]
                            ]

                        # Final check: ensure no empty strings remain (InfluxDB rejects empty tags)
                        if any(v == "" for v in time_series_data[tag_col]):
                            logger.warning(
                                f"Found empty strings in tag column '{tag_col}' for {item_id}, "
                                "replacing with 'unknown' placeholder"
                            )
                            time_series_data[tag_col] = [
                                "unknown" if v == "" else v
                                for v in time_series_data[tag_col]
                            ]

        try:
            success = influx_client.write(
                data=time_series_data,
                ticker=ticker,
                table=dynamic_table_name,
                tag_columns=tag_columns,
            )

            if success:
                data_count = (
                    len(time_series_data)
                    if isinstance(time_series_data, list)
                    else len(time_series_data.get("datetime", []))
                )
                logger.info(f"Successfully wrote {data_count} records for {ticker}")
                processed_count += 1
            else:
                logger.error(f"Failed to write data for {ticker} to InfluxDB")
                failed_count += 1

            queue_broker.delete_data(queue_name, item_id)

        except Exception as e:
            logger.error(f"Error processing {item_id}: {e}")
            queue_broker.delete_data(queue_name, item_id)
            failed_count += 1

    logger.info(
        f"Queue '{queue_name}' processing complete: "
        f"{processed_count} successful, {failed_count} failed"
    )

    return processed_count, failed_count
