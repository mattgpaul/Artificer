"""Diagnostic script to investigate missing OHLCV data in InfluxDB.

This script checks:
1. Redis queue status for ohlcv_queue
2. InfluxDB database contents
3. Bad tickers in MySQL
4. Publisher daemon status
5. Data format issues
"""

import sys
from typing import Any

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.cli_utils import get_sp500_tickers
from system.algo_trader.domain.datasource.sec.tickers.main import Tickers
from system.algo_trader.infra.database.influx.market_data_influx import MarketDataInflux
from system.algo_trader.infra.database.mysql.bad_ticker_client import BadTickerClient
from system.algo_trader.infra.database.redis.queue_broker import QueueBroker


def check_redis_queue(queue_broker: QueueBroker) -> dict[str, Any]:
    """Check Redis ohlcv_queue status."""
    queue_name = "ohlcv_queue"

    size = queue_broker.get_queue_size(queue_name)
    peek_items = queue_broker.peek_queue(queue_name, count=10)

    sample_data = []
    for item_id in peek_items[:3]:
        data = queue_broker.get_data(queue_name, item_id)
        if data:
            sample_info = {
                "item_id": item_id,
                "ticker": data.get("ticker"),
                "has_candles": "candles" in data,
                "candles_type": type(data.get("candles")).__name__ if "candles" in data else None,
            }
            if "candles" in data:
                candles = data["candles"]
                if isinstance(candles, list):
                    sample_info["candles_count"] = len(candles)
                    if len(candles) > 0:
                        sample_info["first_candle_keys"] = (
                            list(candles[0].keys()) if isinstance(candles[0], dict) else None
                        )
                else:
                    sample_info["candles_structure"] = "not a list"
            sample_data.append(sample_info)

    return {
        "queue_name": queue_name,
        "size": size,
        "sample_items": peek_items[:10],
        "sample_data": sample_data,
    }


def check_influxdb_tickers(influx_client: MarketDataInflux) -> dict[str, Any]:
    """Check which tickers exist in InfluxDB."""
    logger = get_logger("Diagnostics")

    # Query for distinct tickers
    query = "SELECT DISTINCT ticker FROM ohlcv"

    try:
        df = influx_client.query(query)
        if df is None or (isinstance(df, bool) and not df) or df.empty:
            return {"ticker_count": 0, "tickers": []}

        tickers = df["ticker"].unique().tolist() if "ticker" in df.columns else []
        return {
            "ticker_count": len(tickers),
            "tickers": sorted(tickers),
        }
    except Exception as e:
        logger.error(f"Error querying InfluxDB: {e}")
        return {"error": str(e)}


def check_bad_tickers() -> dict[str, Any]:
    """Check bad tickers in MySQL."""
    logger = get_logger("Diagnostics")

    try:
        bad_ticker_client = BadTickerClient()
        bad_tickers = bad_ticker_client.get_bad_tickers(limit=10000)

        return {
            "count": len(bad_tickers),
            "tickers": [bt["ticker"] for bt in bad_tickers],
        }
    except Exception as e:
        logger.error(f"Error checking bad tickers: {e}")
        return {"error": str(e)}


def get_sec_registry_tickers() -> dict[str, Any]:
    """Get all tickers from SEC registry.

    Retrieves ticker symbols from SEC company facts datasource and returns
    a dictionary with count and sorted list of unique tickers.

    Returns:
        Dictionary with 'count' and 'tickers' keys, or 'error' key if retrieval fails.
    """
    logger = get_logger("Diagnostics")

    try:
        ticker_source = Tickers()
        all_tickers_data = ticker_source.get_tickers()

        if all_tickers_data is None:
            return {"error": "Failed to retrieve tickers from SEC"}

        ticker_list = []
        for _key, value in all_tickers_data.items():
            if isinstance(value, dict) and "ticker" in value:
                ticker_list.append(value["ticker"])

        return {
            "count": len(ticker_list),
            "tickers": sorted(set(ticker_list)),
        }
    except Exception as e:
        logger.error(f"Error getting SEC registry tickers: {e}")
        return {"error": str(e)}


def check_data_format_issue(queue_broker: QueueBroker) -> dict[str, Any]:
    """Check if there's a data format issue with candles."""
    queue_name = "ohlcv_queue"

    issues = []

    # Check a few items in the queue
    peek_items = queue_broker.peek_queue(queue_name, count=5)
    for item_id in peek_items:
        data = queue_broker.get_data(queue_name, item_id)
        if not data:
            continue

        candles = data.get("candles")
        if candles is None:
            issues.append(f"{item_id}: No 'candles' key in data")
            continue

        if not isinstance(candles, list):
            issues.append(f"{item_id}: candles is not a list (type: {type(candles).__name__})")
            continue

        if len(candles) == 0:
            issues.append(f"{item_id}: candles list is empty")
            continue

        # Check structure of first candle
        if not isinstance(candles[0], dict):
            issues.append(
                f"{item_id}: candles[0] is not a dict (type: {type(candles[0]).__name__})"
            )
            continue

        if "datetime" not in candles[0]:
            issues.append(f"{item_id}: candles[0] missing 'datetime' key")
            continue

    return {
        "issues_found": len(issues),
        "issues": issues,
    }


def main() -> int:  # noqa: C901, PLR0912, PLR0915
    """Run diagnostic checks for missing OHLCV data.

    Executes comprehensive diagnostic checks including Redis queue status,
    InfluxDB contents, bad tickers, S&P 500 comparison, and data format issues.
    Prints formatted report to stdout.

    Returns:
        Exit code (0 for success).
    """
    print("\n" + "=" * 80)
    print("OHLCV Data Diagnostic Report")
    print("=" * 80 + "\n")

    queue_broker = None
    influx_status = {}
    bad_tickers_status = {}

    print("1. Redis Queue Status")
    print("-" * 80)
    try:
        queue_broker = QueueBroker(namespace="queue")
        redis_status = check_redis_queue(queue_broker)
        print(f"Queue: {redis_status['queue_name']}, Pending: {redis_status['size']}")
        if redis_status["size"] > 0:
            print(f"Sample: {', '.join(redis_status['sample_items'][:5])}")
        print()
    except Exception as e:
        print(f"❌ Error: {e}\n")

    print("2. InfluxDB Database Contents")
    print("-" * 80)
    try:
        influx_client = MarketDataInflux(database="ohlcv")
        influx_status = check_influxdb_tickers(influx_client)
        if "error" in influx_status:
            print(f"❌ Error: {influx_status['error']}")
        else:
            print(f"Tickers: {influx_status['ticker_count']}")
            if influx_status["ticker_count"] > 0:
                print(f"Sample: {', '.join(influx_status['tickers'][:10])}")
        print()
    except Exception as e:
        print(f"❌ Error: {e}\n")

    print("3. Bad Tickers in MySQL")
    print("-" * 80)
    try:
        bad_tickers_status = check_bad_tickers()
        if "error" in bad_tickers_status:
            print(f"❌ Error: {bad_tickers_status['error']}")
        else:
            print(f"Count: {bad_tickers_status['count']}")
            if bad_tickers_status["count"] > 0:
                print(f"Sample: {', '.join(bad_tickers_status['tickers'][:10])}")
        print()
    except Exception as e:
        print(f"❌ Error: {e}\n")

    print("4. S&P 500 Ticker Comparison")
    print("-" * 80)
    try:
        sp500_tickers = get_sp500_tickers()
        print(f"Total: {len(sp500_tickers)}")
        if "ticker_count" in influx_status and "tickers" in bad_tickers_status:
            influx_tickers = set(influx_status.get("tickers", []))
            sp500_set = set(sp500_tickers)
            missing = sp500_set - influx_tickers
            bad_ticker_set = set(bad_tickers_status["tickers"])
            print(f"Missing: {len(missing)}")
            if len(missing) > 0:
                print(f"Tickers: {', '.join(sorted(missing))}")
                missing_in_bad = missing & bad_ticker_set
                missing_not_in_bad = missing - bad_ticker_set
                missing_in_bad_str = ", ".join(sorted(missing_in_bad)) if missing_in_bad else "none"
                print(f"In bad_tickers: {len(missing_in_bad)} ({missing_in_bad_str})")
                missing_not_in_bad_str = (
                    ", ".join(sorted(missing_not_in_bad)) if missing_not_in_bad else "none"
                )
                print(f"NOT in bad_tickers: {len(missing_not_in_bad)} ({missing_not_in_bad_str})")
        print()
    except Exception as e:
        print(f"❌ Error: {e}\n")

    print("5. Cross-Correlation: SEC Registry vs Bad Tickers + InfluxDB")
    print("-" * 80)
    try:
        sec_status = get_sec_registry_tickers()
        if "error" in sec_status:
            print(f"❌ Error: {sec_status['error']}")
        elif "tickers" in bad_tickers_status and "tickers" in influx_status:
            sec_tickers = set(sec_status["tickers"])
            bad_ticker_set = set(bad_tickers_status["tickers"])
            influx_ticker_set = set(influx_status["tickers"])
            accounted_for = bad_ticker_set | influx_ticker_set
            missing_from_accounting = sec_tickers - accounted_for
            extra_tickers = accounted_for - sec_tickers

            print(
                f"SEC Registry: {len(sec_tickers)}, "
                f"Bad: {len(bad_ticker_set)}, "
                f"InfluxDB: {len(influx_ticker_set)}"
            )
            print(f"Accounted for (bad | influx): {len(accounted_for)}")

            overlap = bad_ticker_set & influx_ticker_set
            if len(overlap) > 0:
                print(f"⚠️  Overlap (in both bad_tickers AND InfluxDB): {len(overlap)}")

            if len(missing_from_accounting) > 0:
                print(f"❌ Missing from accounting: {len(missing_from_accounting)}")
                print(f"Sample missing: {', '.join(sorted(missing_from_accounting)[:50])}")
                if len(missing_from_accounting) > 50:
                    print(f"... and {len(missing_from_accounting) - 50} more")
                try:
                    bad_ticker_client = BadTickerClient()
                    stored = bad_ticker_client.store_missing_tickers(
                        sorted(missing_from_accounting), "diagnostic_cross_correlation"
                    )
                    print(f"✅ Stored {stored} missing tickers in missing_tickers table")
                except Exception as e:
                    print(f"❌ Error storing: {e}")

            if len(extra_tickers) > 0:
                print(
                    f"⚠️  Extra tickers (in bad/influx but NOT in SEC registry): "
                    f"{len(extra_tickers)}"
                )
                print(f"Sample extra: {', '.join(sorted(extra_tickers)[:20])}")
                if len(extra_tickers) > 20:
                    print(f"... and {len(extra_tickers) - 20} more")

            if len(missing_from_accounting) > 0:
                print(f"❌ DATA LOSS: {len(missing_from_accounting)} SEC registry tickers missing")
            elif len(extra_tickers) > 0:
                print(f"⚠️  Mismatch: {len(extra_tickers)} extra tickers not in SEC registry")
            else:
                print("✅ All SEC registry tickers accounted for, no extras")
        print()
    except Exception as e:
        print(f"❌ Error: {e}\n")

    print("6. Data Format Issues")
    print("-" * 80)
    format_issues = {"issues_found": 0}
    if queue_broker:
        try:
            format_issues = check_data_format_issue(queue_broker)
            if format_issues["issues_found"] > 0:
                print(f"⚠️  Found {format_issues['issues_found']} issues")
                for issue in format_issues["issues"][:5]:
                    print(f"  - {issue}")
            else:
                print("No issues found")
        except Exception as e:
            print(f"❌ Error: {e}")
    print()

    print("7. Recommendations")
    print("-" * 80)
    if influx_status.get("ticker_count", 0) < 100:
        print("⚠️  Very few tickers in InfluxDB - check publisher logs")
    if format_issues.get("issues_found", 0) > 0:
        print("⚠️  Data format issues detected")
    print()

    print("=" * 80)
    print("Diagnostic complete")
    print("=" * 80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
