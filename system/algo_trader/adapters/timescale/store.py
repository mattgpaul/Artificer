"""TimescaleDB store for algo_trader.

Provides persistent storage for bars, decisions, overrides, and fills using
TimescaleDB hypertables for time-series data.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from infrastructure.postgres.postgres import BasePostgresClient
from system.algo_trader.adapters.timescale.migrations import MIGRATIONS
from system.algo_trader.domain.models import Bar, Fill


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _sanitize_schema_fragment(value: str) -> str:
    out = []
    for ch in value.strip().lower():
        if ("a" <= ch <= "z") or ("0" <= ch <= "9") or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    s = "".join(out).strip("_")
    return s or "default"


@dataclass(slots=True)
class AlgoTraderStore:
    """Primary durable store (Postgres+TimescaleDB)."""

    db: BasePostgresClient
    schema: str = "public"

    @staticmethod
    def schema_for_engine(engine_id: str) -> str:
        """Return the schema name for a given engine_id."""
        frag = _sanitize_schema_fragment(engine_id)
        return f"algo_trader_{frag}"

    def _schema_q(self) -> str:
        """Return quoted schema name for SQL safety."""
        # `schema` is sanitized, but we still quote it for correctness.
        return f'"{self.schema}"'

    def migrate(self) -> None:
        """Run database migrations to create tables and hypertables."""
        if self.schema != "public":
            self.db.execute(f"CREATE SCHEMA IF NOT EXISTS {self._schema_q()};")
        for stmt in MIGRATIONS:
            self.db.execute(stmt.format(schema=self.schema, schema_q=self._schema_q()))

    def create_run(self, run_id: str, mode: str, config: dict[str, Any]) -> None:
        """Create a new run record in the database."""
        self.db.execute(
            f"""
            INSERT INTO {self._schema_q()}.run(run_id, mode, created_at, config_json)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT(run_id) DO NOTHING
            """,
            (run_id, mode, _utc_now(), json.dumps(config)),
        )

    def upsert_symbols(self, symbols: dict[str, dict[str, Any]]) -> None:
        """Upsert symbol metadata to the database."""
        now = _utc_now()
        for sym, meta in symbols.items():
            self.db.execute(
                f"""
                INSERT INTO {self._schema_q()}.symbols(symbol, meta, updated_at)
                VALUES (%s, %s::jsonb, %s)
                ON CONFLICT(symbol) DO UPDATE SET
                  meta = EXCLUDED.meta,
                  updated_at = EXCLUDED.updated_at
                """,
                (sym, json.dumps(meta), now),
            )

    def upsert_daily_bars(self, bars: Iterable[Bar]) -> None:
        """Upsert daily bars to the database."""
        for b in bars:
            self.db.execute(
                f"""
                INSERT INTO {self._schema_q()}.ohlcv_daily(
                    symbol, day, open, high, low, close, volume
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(symbol, day) DO UPDATE SET
                  open = EXCLUDED.open,
                  high = EXCLUDED.high,
                  low = EXCLUDED.low,
                  close = EXCLUDED.close,
                  volume = EXCLUDED.volume
                """,
                (b.symbol, b.day, b.open, b.high, b.low, b.close, b.volume),
            )

    def get_daily_bars(self, symbols: Sequence[str], start: date, end: date) -> list[Bar]:
        """Retrieve daily bars for symbols within date range."""
        rows = self.db.fetchall(
            f"""
            SELECT symbol, day, open, high, low, close, volume
            FROM {self._schema_q()}.ohlcv_daily
            WHERE symbol = ANY(%s) AND day >= %s AND day <= %s
            ORDER BY day ASC
            """,
            (list(symbols), start, end),
        )
        out: list[Bar] = []
        for r in rows:
            out.append(
                Bar(
                    symbol=r["symbol"],
                    day=r["day"],
                    open=Decimal(str(r["open"])),
                    high=Decimal(str(r["high"])),
                    low=Decimal(str(r["low"])),
                    close=Decimal(str(r["close"])),
                    volume=int(r["volume"]),
                )
            )
        return out

    def record_fill(self, fill: Fill, run_id: str | None = None) -> None:
        """Record a fill to the trade_execution table."""
        self.db.execute(
            f"""
            INSERT INTO {self._schema_q()}.trade_execution(ts, run_id, symbol, side, qty, price)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (fill.ts, run_id, fill.symbol, fill.side.value, fill.qty, fill.price),
        )
