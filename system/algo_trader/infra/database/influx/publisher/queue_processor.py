"""Queue processor for InfluxDB publisher.

This module provides functionality to process Redis queues and write data
to InfluxDB, handling various data formats and error conditions.
"""

from collections.abc import Callable
from typing import Any

from infrastructure.influxdb.influxdb import BatchWriteConfig
from infrastructure.logging.logger import get_logger
from system.algo_trader.infra.database.influx.market_data_influx import MarketDataInflux
from system.algo_trader.infra.database.redis.queue_broker import QueueBroker


def process_queue(
    queue_config: dict[str, Any],
    queue_broker: QueueBroker,
    influx_client: MarketDataInflux,
    is_running: Callable[[], bool],
    logger=None,
) -> tuple[int, int]:
    """Process items from Redis queue and write to InfluxDB.

    Dequeues items from Redis queue, validates data structure, and writes
    to InfluxDB. Handles various data formats (candles, data) and error conditions.

    Args:
        queue_config: Dictionary containing queue configuration with 'name' and 'table'.
        queue_broker: QueueBroker instance for Redis operations.
        influx_client: MarketDataInflux client for writing to InfluxDB.
        is_running: Callable that returns True if processing should continue.
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

    while is_running():
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
        target_database = data.get("database")

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
                    portfolio_stage = data.get("portfolio_stage")
                    if portfolio_stage == "phase1":
                        dynamic_table_name = "local_trades"
                    else:
                        dynamic_table_name = "trades"
                elif queue_name == "backtest_metrics_queue":
                    dynamic_table_name = f"{strategy_name}_summary"
                elif queue_name == "backtest_studies_queue":
                    # Strategy-specific studies live in per-strategy measurements.
                    dynamic_table_name = strategy_name

            backtest_id = data.get("backtest_id")
            hash_value = data.get("hash") or data.get("hash_id")

            data_length = len(time_series_data.get("datetime", []))
            if data_length == 0:
                logger.warning(f"Empty datetime array in {item_id}, skipping")
                queue_broker.delete_data(queue_name, item_id)
                failed_count += 1
                continue

            # backtest_id is deprecated for new schema; do not add it as a tag or field
            # for trades or studies. It may still be used for legacy metrics only.
            if backtest_id and queue_name == "backtest_metrics_queue":
                if "backtest_id" not in time_series_data:
                    time_series_data["backtest_id"] = [backtest_id] * data_length
                tag_columns.append("backtest_id")
            if hash_value:
                if "hash" not in time_series_data:
                    time_series_data["hash"] = [hash_value] * data_length
                tag_columns.append("hash")

            if strategy_name:
                if "strategy" not in time_series_data:
                    time_series_data["strategy"] = [strategy_name] * data_length
                tag_columns.append("strategy")

            # Add strategy parameters as tags if provided.
            # For the new schema:
            # - Trades: do NOT tag with strategy parameters; those belong in
            #   strategy-specific tables, not in the shared trades measurement.
            # - Studies/metrics: keep parameter tags (e.g., short_window/long_window)
            #   but skip side, which is already expressed in trades.
            strategy_params = data.get("strategy_params")
            if (
                strategy_params
                and isinstance(strategy_params, dict)
                and queue_name != "backtest_trades_queue"
            ):
                for raw_key, param_value in strategy_params.items():
                    # Skip side for strategy tables/metrics; side is a trade-level concept.
                    if raw_key == "side":
                        continue

                    # Preserve historic tag names for SMA crossover parameters to
                    # avoid line protocol issues and maintain dashboard queries.
                    if raw_key == "short":
                        param_key = "short_window"
                    elif raw_key == "long":
                        param_key = "long_window"
                    else:
                        param_key = raw_key

                    # Convert param value to string for tag storage
                    param_str = str(param_value)
                    if param_key not in time_series_data:
                        time_series_data[param_key] = [param_str] * data_length
                    tag_columns.append(param_key)

            if queue_name == "backtest_studies_queue":
                field_candidates = [
                    key
                    for key in time_series_data.keys()
                    if key not in tag_columns and key != "datetime"
                ]
                logger.debug(
                    f"backtest_studies_queue payload for {ticker}: "
                    f"fields={field_candidates}, tags={tag_columns}"
                )

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
                                "unknown" if (v is None or v == "") else str(v) for v in tag_values
                            ]
                        else:
                            # Ensure all tag values are strings
                            time_series_data[tag_col] = [str(v) for v in time_series_data[tag_col]]

                        # Final check: ensure no empty strings remain (InfluxDB rejects empty tags)
                        if any(v == "" for v in time_series_data[tag_col]):
                            logger.warning(
                                f"Found empty strings in tag column '{tag_col}' for {item_id}, "
                                "replacing with 'unknown' placeholder"
                            )
                            time_series_data[tag_col] = [
                                "unknown" if v == "" else v for v in time_series_data[tag_col]
                            ]

        try:
            # Use target database client if specified, otherwise use default
            client_to_use = influx_client
            if target_database and target_database != influx_client.database:
                logger.info(
                    f"Creating client for target database '{target_database}' "
                    f"(default was '{influx_client.database}')"
                )

                write_config = BatchWriteConfig(
                    batch_size=50000,
                    flush_interval=10000,
                )
                client_to_use = MarketDataInflux(
                    database=target_database, write_config=write_config
                )

            success = client_to_use.write(
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

        # Check shutdown flag after each item to allow quick exit
        if not is_running():
            break

    logger.info(
        f"Queue '{queue_name}' processing complete: "
        f"{processed_count} successful, {failed_count} failed"
    )

    return processed_count, failed_count
