"""Algo Trader - Phase 4: Grafana Visualization.

Entry point for collecting historical market data from Schwab API,
fetching ticker list from SEC, storing both in InfluxDB, and
setting up Grafana visualization for long-term analysis.
"""

import random
import sys

from infrastructure.logging.logger import get_logger
from system.algo_trader.clients.grafana_client import AlgoTraderGrafanaClient
from system.algo_trader.clients.influxdb_client import AlgoTraderInfluxDBClient, CandleSeriesSpec
from system.algo_trader.clients.redis_client import AlgoTraderRedisClient
from system.algo_trader.clients.schwab_client import AlgoTraderSchwabClient
from system.algo_trader.datasources.sec import SECDataSource


def _select_tickers(
    sec_tickers: list[dict],
    *,
    known_tickers: list[str],
    random_count: int,
    logger,
) -> tuple[list[str], list[str], list[str]]:
    sec_symbols = [
        t["ticker"] for t in sec_tickers if t.get("ticker") and t["ticker"] not in known_tickers
    ]
    random_tickers = random.sample(sec_symbols, min(random_count, len(sec_symbols)))
    all_tickers = known_tickers + random_tickers
    logger.info("Selected tickers for Phase 4:")
    logger.info(f"  Known tickers: {known_tickers}")
    logger.info(f"  Random tickers: {random_tickers}")
    logger.info(f"  Total tickers: {len(all_tickers)}")
    return all_tickers, known_tickers, random_tickers


def _fetch_and_store_market_data(
    *,
    tickers: list[str],
    market_data_specs: list[CandleSeriesSpec],
    logger,
    schwab_client: AlgoTraderSchwabClient,
    influx_client: AlgoTraderInfluxDBClient,
) -> tuple[int, int]:
    total_candles = 0
    successful_writes = 0

    for ticker in tickers:
        logger.info(f"\nProcessing ticker: {ticker}")
        for spec in market_data_specs:
            logger.info(
                f"  Fetching {ticker} data: "
                f"{spec.period}{spec.period_type}, {spec.frequency}{spec.frequency_type}"
            )

            price_data = schwab_client.get_price_history(
                symbol=ticker,
                period_type=spec.period_type,
                period=spec.period,
                frequency_type=spec.frequency_type,
                frequency=spec.frequency,
            )

            if not price_data or "candles" not in price_data:
                logger.warning(f"  No data retrieved for {ticker}")
                continue

            candles = price_data["candles"]
            logger.info(f"  Retrieved {len(candles)} candles for {ticker}")

            success = influx_client.write_candle_data(ticker=ticker, spec=spec, candles=candles)
            if success:
                successful_writes += 1
                total_candles += len(candles)
            else:
                logger.error(f"  Failed to write {ticker} data to InfluxDB")

    return successful_writes, total_candles


def _require_redis(redis_client: AlgoTraderRedisClient, *, logger) -> bool:
    if redis_client.ping():
        logger.info("Redis connection successful")
        return True
    logger.error("Failed to connect to Redis")
    return False


def _fetch_sec_and_select_tickers(
    *,
    sec_source: SECDataSource,
    known_tickers: list[str],
    logger,
) -> tuple[list[dict] | None, list[str] | None, list[str] | None]:
    logger.info("\n" + "=" * 60)
    logger.info("Phase 4: Fetching SEC Ticker List and Selecting Random Tickers")
    logger.info("=" * 60)

    sec_tickers = sec_source.fetch_tickers()
    if sec_tickers is None:
        logger.error("Failed to fetch SEC ticker list")
        return None, None, None

    logger.info(f"Fetched {len(sec_tickers)} tickers from SEC")
    if not sec_source.store_tickers_in_influxdb(sec_tickers):
        logger.error("Failed to store SEC ticker list in InfluxDB")
        return None, None, None

    logger.info("Successfully stored ticker metadata in InfluxDB")
    all_tickers, _known, random_tickers = _select_tickers(
        sec_tickers,
        known_tickers=known_tickers,
        random_count=5,
        logger=logger,
    )
    return sec_tickers, all_tickers, random_tickers


def _demo_filtering(*, influx_client: AlgoTraderInfluxDBClient, tickers: list[str], logger) -> None:
    logger.info("\nDemonstrating ticker filtering capability:")
    logger.info("Querying market data for tickers in SEC list...")
    for ticker in tickers:
        sql = f"SELECT ticker FROM ticker_metadata WHERE ticker = '{ticker}' LIMIT 1"
        metadata = influx_client.query(sql)
        if metadata is None or len(metadata) <= 0:
            continue

        sql = f"SELECT COUNT(*) as count FROM market_data WHERE ticker = '{ticker}'"
        candle_count = influx_client.query(sql)
        if candle_count is None or len(candle_count) <= 0:
            continue

        count = candle_count.iloc[0]["count"]
        logger.info(f"  {ticker}: Found in SEC list, {count} candles in database")


def _setup_grafana(*, grafana_client: AlgoTraderGrafanaClient, logger) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("Phase 4: Setting up Grafana Visualization")
    logger.info("=" * 60)

    if not grafana_client.setup_visualization():
        logger.error("Failed to setup Grafana visualization")
        return False

    logger.info("Grafana visualization setup completed successfully")
    dashboard_url = grafana_client.get_dashboard_url()
    logger.info(f"Access your market data dashboard at: {dashboard_url}")
    logger.info(f"Grafana admin interface: {grafana_client.host}")
    logger.info(f"Admin credentials: {grafana_client.admin_user} / {grafana_client.admin_password}")
    return True


def main() -> int:
    """Run the Phase 4 algo_trader flow.

    Fetch SEC ticker list, collect market data for selected tickers, store results
    in InfluxDB, and set up Grafana visualization.
    """
    logger = get_logger("AlgoTraderMain")

    # Phase 4 Configuration: 8 tickers (5 random + 3 known), each with 3 timeframes
    known_tickers = ["AAPL", "MSFT", "GOOGL"]

    # Phase 4 timeframes as specified: 1d:5yr, 1wk:10yr, 1mo:20yr
    market_data_specs = [
        CandleSeriesSpec(
            period_type="year", period=5, frequency_type="daily", frequency=1
        ),  # 1d:5yr
        CandleSeriesSpec(
            period_type="year", period=10, frequency_type="weekly", frequency=1
        ),  # 1wk:10yr
        CandleSeriesSpec(
            period_type="year", period=20, frequency_type="monthly", frequency=1
        ),  # 1mo:20yr
    ]

    logger.info("Algo Trader Phase 4: Starting")

    # Initialize clients
    redis_client = AlgoTraderRedisClient()
    schwab_client = AlgoTraderSchwabClient(redis_client)
    influx_client = AlgoTraderInfluxDBClient()
    grafana_client = AlgoTraderGrafanaClient()
    sec_source = SECDataSource(influxdb_client=influx_client)

    if not _require_redis(redis_client, logger=logger):
        return 1

    # Note: Authentication is handled automatically by schwab_client when needed
    # It will trigger OAuth2 flow if refresh token is missing or invalid
    sec_tickers, all_tickers, random_tickers = _fetch_sec_and_select_tickers(
        sec_source=sec_source,
        known_tickers=known_tickers,
        logger=logger,
    )
    if sec_tickers is None or all_tickers is None or random_tickers is None:
        return 1

    logger.info("\n" + "=" * 60)
    logger.info("Phase 4: Fetching Market Data for 8 Tickers")
    logger.info("=" * 60)

    # Fetch and store data for each ticker and configuration
    successful_writes, total_candles = _fetch_and_store_market_data(
        tickers=all_tickers,
        market_data_specs=market_data_specs,
        logger=logger,
        schwab_client=schwab_client,
        influx_client=influx_client,
    )

    # Summary
    expected_writes = len(all_tickers) * len(market_data_specs)
    logger.info(f"\n{'=' * 60}")
    logger.info("Phase 4 Summary:")
    logger.info(f"  SEC tickers fetched: {len(sec_tickers)}")
    logger.info("  Ticker metadata stored: True")
    logger.info(f"  Market data tickers processed: {len(all_tickers)}")
    logger.info(f"  Known tickers: {known_tickers}")
    logger.info(f"  Random tickers: {random_tickers}")
    logger.info(f"  Successful market data writes: {successful_writes}/{expected_writes}")
    logger.info(f"  Total candles stored: {total_candles}")
    logger.info(f"{'=' * 60}")

    _demo_filtering(influx_client=influx_client, tickers=all_tickers, logger=logger)

    # Close InfluxDB connection
    influx_client.close()

    if not _setup_grafana(grafana_client=grafana_client, logger=logger):
        return 1

    if successful_writes == expected_writes:
        logger.info("Phase 4 completed successfully")
        print("\nPhase 4 completed successfully!")
        print(f"View your market data at: {grafana_client.get_dashboard_url()}")
        return 0
    else:
        logger.error(
            f"Phase 4 completed with errors ({successful_writes}/{expected_writes} successful)"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
