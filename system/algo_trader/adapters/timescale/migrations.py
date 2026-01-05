"""TimescaleDB migration SQL statements.

Contains SQL DDL statements for creating TimescaleDB hypertables and related
tables for algo_trader data storage.
"""

from __future__ import annotations

MIGRATIONS: list[str] = [
    """
    CREATE EXTENSION IF NOT EXISTS timescaledb;
    """,
    """
    CREATE TABLE IF NOT EXISTS {schema_q}.run (
      run_id TEXT PRIMARY KEY,
      mode TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL,
      config_json JSONB NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS {schema_q}.symbols (
      symbol TEXT PRIMARY KEY,
      meta JSONB NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS {schema_q}.ohlcv_daily (
      symbol TEXT NOT NULL,
      day DATE NOT NULL,
      open NUMERIC NOT NULL,
      high NUMERIC NOT NULL,
      low NUMERIC NOT NULL,
      close NUMERIC NOT NULL,
      volume BIGINT NOT NULL,
      PRIMARY KEY (symbol, day)
    );
    """,
    """
    SELECT create_hypertable('{schema}.ohlcv_daily', by_range('day'), if_not_exists => TRUE);
    """,
    """
    CREATE TABLE IF NOT EXISTS {schema_q}.decision_event (
      ts TIMESTAMPTZ NOT NULL,
      run_id TEXT NULL,
      payload JSONB NOT NULL
    );
    """,
    """
    SELECT create_hypertable('{schema}.decision_event', by_range('ts'), if_not_exists => TRUE);
    """,
    """
    CREATE TABLE IF NOT EXISTS {schema_q}.override_event (
      ts TIMESTAMPTZ NOT NULL,
      run_id TEXT NULL,
      command TEXT NOT NULL,
      args JSONB NOT NULL
    );
    """,
    """
    SELECT create_hypertable('{schema}.override_event', by_range('ts'), if_not_exists => TRUE);
    """,
    """
    CREATE TABLE IF NOT EXISTS {schema_q}.trade_execution (
      ts TIMESTAMPTZ NOT NULL,
      run_id TEXT NULL,
      symbol TEXT NOT NULL,
      side TEXT NOT NULL,
      qty NUMERIC NOT NULL,
      price NUMERIC NOT NULL
    );
    """,
    """
    SELECT create_hypertable('{schema}.trade_execution', by_range('ts'), if_not_exists => TRUE);
    """,
]
