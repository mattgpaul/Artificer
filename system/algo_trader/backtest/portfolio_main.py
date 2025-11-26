#!/usr/bin/env python3

import argparse
import sys
import time

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.backtest.core.data_loader import DataLoader
from system.algo_trader.backtest.core.execution import ExecutionConfig
from system.algo_trader.backtest.processor.processor import get_backtest_database
from system.algo_trader.backtest.results.writer import ResultsWriter
from system.algo_trader.backtest.utils.utils import BACKTEST_TRADES_QUEUE_NAME
from system.algo_trader.influx.market_data_influx import MarketDataInflux
from system.algo_trader.redis.queue_broker import QueueBroker
from system.algo_trader.strategy.portfolio_manager.config_loader import (
    load_portfolio_manager_config,
)
from system.algo_trader.strategy.portfolio_manager.portfolio_manager import PortfolioManager


def parse_args():
    parser = argparse.ArgumentParser(
        description="Portfolio manager phase-2 for backtest trades"
    )
    parser.add_argument(
        "--hash",
        dest="hashes",
        action="append",
        required=True,
        help="Backtest hash ID to include (can be specified multiple times)",
    )
    parser.add_argument(
        "--portfolio-manager",
        type=str,
        required=True,
        help="Portfolio manager YAML config name or path",
    )
    parser.add_argument(
        "--database",
        type=str,
        default=None,
        help="InfluxDB database with local_trades (default: backtest-dev)",
    )
    parser.add_argument(
        "--ohlcv-database",
        type=str,
        default="ohlcv",
        help="InfluxDB database for OHLCV data (default: ohlcv)",
    )
    parser.add_argument(
        "--initial-account-value",
        type=float,
        default=10000.0,
        help="Initial account value for portfolio (default: 100000)",
    )
    return parser.parse_args()


def load_phase1_executions(
    database: str,
    hashes: list[str],
    logger,
    max_wait_seconds: int = 30,
    poll_interval_seconds: float = 2.0,
) -> pd.DataFrame:
    client = MarketDataInflux(database=database)
    all_executions = []

    for hash_id in hashes:
        query = f'SELECT * FROM "local_trades" WHERE hash = \'{hash_id}\' ORDER BY time ASC'

        df = None
        start_time = time.time()

        while True:
            df = client.query(query)

            if isinstance(df, pd.DataFrame) and not df.empty:
                break

            elapsed = time.time() - start_time
            if elapsed >= max_wait_seconds:
                logger.warning(
                    f"No phase-1 executions found for hash {hash_id} after "
                    f"waiting {int(elapsed)} seconds"
                )
                df = None
                break

            logger.info(
                f"Waiting for phase-1 executions for hash {hash_id} "
                f"(elapsed={int(elapsed)}s)..."
            )
            time.sleep(poll_interval_seconds)

        if df is None:
            continue

        if "time" in df.columns:
            df["signal_time"] = pd.to_datetime(df["time"], utc=True)
            df = df.drop("time", axis=1)
        elif "datetime" in df.columns:
            df["signal_time"] = pd.to_datetime(df["datetime"], utc=True)
            if "datetime" in df.columns:
                df = df.drop("datetime", axis=1)

        all_executions.append(df)

    client.close()

    if not all_executions:
        return pd.DataFrame()

    combined = pd.concat(all_executions, ignore_index=True)
    logger.info(f"Loaded {len(combined)} phase-1 executions from {len(hashes)} hash(es)")
    return combined


def load_ohlcv_for_executions(
    executions: pd.DataFrame, ohlcv_database: str, hashes: list[str], logger
) -> dict[str, pd.DataFrame]:
    if executions.empty:
        return {}

    tickers = executions["ticker"].unique().tolist()
    if not tickers:
        return {}

    hash_id = hashes[0] if hashes else None
    ohlcv_by_ticker: dict[str, pd.DataFrame] = {}

    if hash_id:
        from system.algo_trader.backtest.ohlcv_cache import load_ohlcv_frame

        for ticker in tickers:
            cached_df = load_ohlcv_frame(hash_id, ticker)
            if cached_df is not None and not cached_df.empty:
                ohlcv_by_ticker[ticker] = cached_df

    missing_tickers = [t for t in tickers if t not in ohlcv_by_ticker]
    if missing_tickers:
        signal_times = executions["signal_time"]
        start_date = signal_times.min()
        end_date = signal_times.max()

        client = MarketDataInflux(database=ohlcv_database)
        loader = DataLoader(client, logger)
        loaded_data = loader.load_ohlcv_data(missing_tickers, start_date, end_date)
        client.close()

        ohlcv_by_ticker.update(loaded_data)

        if hash_id:
            from system.algo_trader.backtest.ohlcv_cache import store_ohlcv_frame

            for ticker, df in loaded_data.items():
                if df is not None and not df.empty:
                    store_ohlcv_frame(hash_id, ticker, df)

    logger.info(f"Loaded OHLCV data for {len(ohlcv_by_ticker)} ticker(s)")
    return ohlcv_by_ticker


def wait_for_phase1_completion(
    hashes: list[str],
    logger,
    max_wait_seconds: int = 60,
    poll_interval_seconds: float = 2.0,
) -> bool:
    broker = QueueBroker(namespace="queue")
    start_time = time.time()

    while True:
        pending_ids = broker.peek_queue(BACKTEST_TRADES_QUEUE_NAME, count=100)
        if not pending_ids:
            return True

        has_phase1_for_hash = False

        for item_id in pending_ids:
            data = broker.get_data(BACKTEST_TRADES_QUEUE_NAME, item_id)
            if not data:
                continue

            stage = data.get("portfolio_stage")
            if stage != "phase1":
                continue

            hash_value = data.get("hash") or data.get("hash_id")
            if hash_value and hash_value in hashes:
                has_phase1_for_hash = True
                break

        if not has_phase1_for_hash:
            return True

        elapsed = time.time() - start_time
        if elapsed >= max_wait_seconds:
            logger.warning(
                "Phase-1 trades queue still has pending items for hashes "
                f"{hashes} after waiting {int(elapsed)} seconds"
            )
            return False

        logger.info(
            "Waiting for phase-1 trades to be flushed from Redis for hashes "
            f"{hashes} (elapsed={int(elapsed)}s)..."
        )
        time.sleep(poll_interval_seconds)


def run_portfolio_phase(
    database: str,
    hashes: list[str],
    portfolio_manager_config: str,
    initial_account_value: float,
    ohlcv_database: str,
    logger,
) -> int:
    logger.info("=" * 80)
    logger.info("Portfolio Manager Phase-2")
    logger.info("=" * 80)

    logger.info(f"Database: {database}")
    logger.info(f"Hashes: {hashes}")
    logger.info(f"Portfolio Manager Config: {portfolio_manager_config}")

    wait_for_phase1_completion(hashes, logger)

    pipeline = load_portfolio_manager_config(portfolio_manager_config, logger)
    if pipeline is None:
        logger.error("Failed to load portfolio manager config")
        return 1

    pm = PortfolioManager(
        pipeline=pipeline,
        initial_account_value=initial_account_value,
        settlement_lag_trading_days=2,
        logger=logger,
    )

    executions = load_phase1_executions(database, hashes, logger)
    if executions.empty:
        logger.warning("No phase-1 executions found for given hashes")
        return 0

    ohlcv_by_ticker = load_ohlcv_for_executions(executions, ohlcv_database, hashes, logger)

    approved = pm.apply(executions, ohlcv_by_ticker)

    if approved.empty:
        logger.warning("Portfolio manager filtered all executions")
        return 0

    logger.info(f"Portfolio manager approved {len(approved)} of {len(executions)} executions")

    writer = ResultsWriter()

    if "strategy" in approved.columns:
        strategy_col = "strategy"
    elif "strategy_name" in approved.columns:
        strategy_col = "strategy_name"
    else:
        logger.error("No strategy column found in approved executions")
        return 1

    for strategy_name in approved[strategy_col].unique():
        df_strat = approved[approved[strategy_col] == strategy_name]
        for ticker in df_strat["ticker"].unique():
            df_t = df_strat[df_strat["ticker"] == ticker]
            hash_id = df_t["hash"].iloc[0] if "hash" in df_t.columns else hashes[0]

            success = writer.write_trades(
                trades=df_t,
                strategy_name=strategy_name,
                ticker=ticker,
                hash_id=hash_id,
                database=database,
                portfolio_stage="final",
            )

            if success:
                logger.info(
                    f"Enqueued {len(df_t)} portfolio-approved executions for "
                    f"{ticker} / {strategy_name} / {hash_id}"
                )
            else:
                logger.error(
                    f"Failed to enqueue portfolio-approved executions for "
                    f"{ticker} / {strategy_name} / {hash_id}"
                )

    total_signals = len(executions)
    approved_signals = len(approved)
    delta = total_signals - approved_signals

    print(f"\n{'=' * 50}")
    print("Portfolio Manager Phase-2 Summary")
    print(f"{'=' * 50}")
    if hashes:
        if len(hashes) == 1:
            print(f"Hash ID: {hashes[0]}")
        else:
            print(f"Hash IDs: {', '.join(hashes)}")
    print(f"Total Signals: {total_signals}")
    print(f"Signals Sent: {approved_signals}")
    print(f"Signals Filtered: {delta}")
    print(f"{'=' * 50}\n")

    logger.info("Portfolio phase-2 complete")
    return 0


def main():
    args = parse_args()
    logger = get_logger("PortfolioPhase2")

    database = args.database or get_backtest_database()

    try:
        return run_portfolio_phase(
            database=database,
            hashes=args.hashes,
            portfolio_manager_config=args.portfolio_manager,
            initial_account_value=args.initial_account_value,
            ohlcv_database=args.ohlcv_database,
            logger=logger,
        )
    except KeyboardInterrupt:
        logger.info("Portfolio phase interrupted by user")
        if args.hashes:
            from system.algo_trader.backtest.ohlcv_cache import clear_for_hash

            for hash_id in args.hashes:
                clear_for_hash(hash_id)
        return 1


if __name__ == "__main__":
    sys.exit(main())

