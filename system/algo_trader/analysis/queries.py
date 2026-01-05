from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from infrastructure.postgres.postgres import BasePostgresClient


@dataclass(slots=True)
class AlgoTraderQueries:
    db: BasePostgresClient

    def list_symbols(self, limit: int = 5000) -> list[str]:
        rows = self.db.fetchall(
            "SELECT symbol FROM symbols ORDER BY symbol ASC LIMIT %s",
            (limit,),
        )
        return [r["symbol"] for r in rows]

    def list_trade_executions(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 5000,
    ) -> pd.DataFrame:
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
            FROM trade_execution
            {where_sql}
            ORDER BY ts ASC
            LIMIT %s
            """,
            tuple(params + [limit]),
        )
        return pd.DataFrame(rows)
