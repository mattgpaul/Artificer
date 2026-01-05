from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from infrastructure.client import Client
from infrastructure.logging.logger import get_logger


class BasePostgresClient(Client):
    """Base Postgres client for database operations (Timescale compatible)."""

    def __init__(self, config=None) -> None:
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)

        if config is None:
            from infrastructure.config import PostgresConfig  # noqa: PLC0415

            config = PostgresConfig()

        self.host = config.host
        self.port = config.port
        self.user = config.user
        self.password = config.password
        self.database = config.database
        self.connect_timeout = config.connect_timeout
        self.autocommit = config.autocommit

        self._conn: psycopg.Connection | None = None

    def _get_connection(self) -> psycopg.Connection:
        if self._conn is None:
            conn_str = (
                f"host={self.host} port={self.port} user={self.user} "
                f"password={self.password} dbname={self.database} connect_timeout={self.connect_timeout}"
            )
            self._conn = psycopg.connect(conn_str, row_factory=dict_row, autocommit=self.autocommit)
            self.logger.info(f"Postgres connection created: {self.host}:{self.port}/{self.database}")
        return self._conn

    def ping(self) -> bool:
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                _ = cur.fetchone()
            return True
        except Exception as e:
            self.logger.debug(f"Postgres ping failed: {e}")
            return False

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> int:
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount

    def fetchone(self, query: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def fetchall(self, query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def begin(self) -> None:
        conn = self._get_connection()
        conn.autocommit = False

    def commit(self) -> None:
        if self._conn is None:
            return
        self._conn.commit()
        self._conn.autocommit = self.autocommit

    def rollback(self) -> None:
        if self._conn is None:
            return
        self._conn.rollback()
        self._conn.autocommit = self.autocommit

    def close(self) -> None:
        if self._conn is None:
            return
        try:
            self._conn.close()
        finally:
            self._conn = None

