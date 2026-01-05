from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Sequence

from infrastructure.postgres.postgres import BasePostgresClient
from system.algo_trader.adapters.timescale.migrations import MIGRATIONS
from system.algo_trader.domain.models import Bar, Fill


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(slots=True)
class AlgoTraderStore:
    """Primary durable store (Postgres+TimescaleDB)."""

    db: BasePostgresClient

    def migrate(self) -> None:
        for stmt in MIGRATIONS:
            self.db.execute(stmt)

    def create_run(self, run_id: str, mode: str, config: dict[str, Any]) -> None:
        self.db.execute(
            """
            INSERT INTO run(run_id, mode, created_at, config_json)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT(run_id) DO NOTHING
            """,
            (run_id, mode, _utc_now(), json.dumps(config)),
        )

    def upsert_symbols(self, symbols: dict[str, dict[str, Any]]) -> None:
        now = _utc_now()
        for sym, meta in symbols.items():
            self.db.execute(
                """
                INSERT INTO symbols(symbol, meta, updated_at)
                VALUES (%s, %s::jsonb, %s)
                ON CONFLICT(symbol) DO UPDATE SET
                  meta = EXCLUDED.meta,
                  updated_at = EXCLUDED.updated_at
                """,
                (sym, json.dumps(meta), now),
            )

    def upsert_daily_bars(self, bars: Iterable[Bar]) -> None:
        for b in bars:
            self.db.execute(
                """
                INSERT INTO ohlcv_daily(symbol, day, open, high, low, close, volume)
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
        rows = self.db.fetchall(
            """
            SELECT symbol, day, open, high, low, close, volume
            FROM ohlcv_daily
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
        self.db.execute(
            """
            INSERT INTO trade_execution(ts, run_id, symbol, side, qty, price)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (fill.ts, run_id, fill.symbol, fill.side.value, fill.qty, fill.price),
        )

