"""Database queries for algo_trader analysis.

Provides query methods for retrieving symbols, trade executions, and other
data from TimescaleDB for analysis and reporting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from infrastructure.postgres.postgres import BasePostgresClient


@dataclass(slots=True)
class AlgoTraderQueries:
    """Query interface for algo_trader TimescaleDB data."""

    db: BasePostgresClient
    schema: str = "public"

    def _schema_q(self) -> str:
        return f'"{self.schema}"'

    def list_symbols(self, limit: int = 5000) -> list[str]:
        """List symbols from the database."""
        rows = self.db.fetchall(
            f"SELECT symbol FROM {self._schema_q()}.symbols ORDER BY symbol ASC LIMIT %s",
            (limit,),
        )
        return [r["symbol"] for r in rows]

    def list_trade_executions(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 5000,
    ) -> pd.DataFrame:
        """List trade executions with optional filtering."""
        where = []
        params: list[Any] = []
        if symbol:
            where.append("symbol = %s")
            params.append(symbol)
        if since:
            where.append("ts >= %s")
            params.append(since)
        where_sql = " WHERE " + " AND ".join(where) if where else ""

        rows = self.db.fetchall(
            f"""
            SELECT ts, symbol, side, qty, price, run_id
            FROM {self._schema_q()}.trade_execution
            {where_sql}
            ORDER BY ts ASC
            LIMIT %s
            """,
            tuple([*params, limit]),
        )
        return pd.DataFrame(rows)
