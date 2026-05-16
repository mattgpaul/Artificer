"""MySQL database client implementation.

Provides a base client class for MySQL database operations with connection
management, transaction support, and query execution methods.
"""

from __future__ import annotations

from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from infrastructure.client import Client
from infrastructure.logging.logger import get_logger


class BaseMySQLClient(Client):
    """Base MySQL client for database operations.

    Provides connection management, transaction support, and query execution
    methods. Supports connection pooling and both autocommit and transaction modes.

    Args:
        config: Optional MySQLConfig instance. If None, creates default config.

    Attributes:
        host: MySQL server hostname.
        port: MySQL server port.
        user: MySQL username.
        password: MySQL password.
        database: Target database name.
        charset: Connection charset.
        connect_timeout: Connection timeout in seconds.
        autocommit: Autocommit mode.
        logger: Logger instance for this client.
        _connection: Internal MySQL connection object.
        _in_transaction: Flag indicating if a transaction is in progress.
    """

    def __init__(self, config=None) -> None:
        """Initialize MySQL client with configuration.

        Args:
            config: Optional MySQLConfig instance. If None, creates default config.
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)

        if config is None:
            from infrastructure.config import MySQLConfig  # noqa: PLC0415

            config = MySQLConfig()

        self.host = config.host
        self.port = config.port
        self.user = config.user
        self.password = config.password
        self.database = config.database
        self.charset = config.charset
        self.connect_timeout = config.connect_timeout
        self.autocommit = config.autocommit

        self._connection: pymysql.Connection | None = None
        self._in_transaction = False

    def _get_connection(self) -> pymysql.Connection:
        """Get or create MySQL connection.

        Returns:
            Active MySQL connection object.
        """
        if self._connection is None:
            self._connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=self.charset,
                connect_timeout=self.connect_timeout,
                autocommit=self.autocommit,
                cursorclass=DictCursor,
            )
            self.logger.info(
                f"MySQL connection created: {self.host}:{self.port}/{self.database} "
                f"(timeout: {self.connect_timeout}s, autocommit: {self.autocommit})"
            )
        return self._connection

    def ping(self) -> bool:
        """Check if database connection is alive.

        Returns:
            True if connection is active, False otherwise.
        """
        try:
            conn = self._get_connection()
            conn.ping(reconnect=False)
            self.logger.debug("MySQL ping successful")
            return True
        except Exception as e:
            self.logger.debug(f"MySQL ping failed: {e}")
            return False

    def execute(self, query: str, params: tuple | None = None) -> int:
        """Execute a single SQL query.

        Args:
            query: SQL query string to execute.
            params: Optional tuple of parameters for parameterized queries.

        Returns:
            Number of rows affected by the query.

        Raises:
            Exception: If query execution fails.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                rowcount = cursor.execute(query, params or ())
                # Only commit if not in autocommit mode and not in explicit transaction
                if not conn.get_autocommit() and not self._in_transaction:
                    conn.commit()
                self.logger.debug(f"EXECUTE: {query[:100]}... -> {rowcount} rows affected")
                return rowcount
        except Exception as e:
            self.logger.error(f"Error executing query '{query[:100]}...': {e}")
            if self._in_transaction:
                self.rollback()
            raise

    def execute_many(self, query: str, params_list: list[tuple]) -> int:
        """Execute a query multiple times with different parameters.

        Args:
            query: SQL query string to execute.
            params_list: List of parameter tuples for each execution.

        Returns:
            Total number of rows affected across all executions.

        Raises:
            Exception: If query execution fails.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                rowcount = cursor.executemany(query, params_list)
                # Only commit if not in autocommit mode and not in explicit transaction
                if not conn.get_autocommit() and not self._in_transaction:
                    conn.commit()
                self.logger.debug(
                    f"EXECUTE_MANY: {query[:100]}... -> {rowcount} rows affected "
                    f"({len(params_list)} executions)"
                )
                return rowcount
        except Exception as e:
            self.logger.error(f"Error executing many queries '{query[:100]}...': {e}")
            if self._in_transaction:
                self.rollback()
            raise

    def fetchone(self, query: str, params: tuple | None = None) -> dict[str, Any] | None:
        """Fetch a single row from the database.

        Args:
            query: SQL SELECT query string.
            params: Optional tuple of parameters for parameterized queries.

        Returns:
            Dictionary representing the row, or None if no row found.

        Raises:
            Exception: If query execution fails.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                row = cursor.fetchone()
                if row:
                    self.logger.debug(f"FETCHONE: {query[:100]}... -> 1 row")
                    return dict(row)
                self.logger.debug(f"FETCHONE: {query[:100]}... -> None")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching one row '{query[:100]}...': {e}")
            raise

    def fetchall(self, query: str, params: tuple | None = None) -> list[dict[str, Any]]:
        """Fetch all rows from the database.

        Args:
            query: SQL SELECT query string.
            params: Optional tuple of parameters for parameterized queries.

        Returns:
            List of dictionaries, each representing a row.

        Raises:
            Exception: If query execution fails.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
                self.logger.debug(f"FETCHALL: {query[:100]}... -> {len(result)} rows")
                return result
        except Exception as e:
            self.logger.error(f"Error fetching all rows '{query[:100]}...': {e}")
            raise

    def fetchmany(
        self, query: str, params: tuple | None = None, size: int = 1
    ) -> list[dict[str, Any]]:
        """Fetch a limited number of rows from the database.

        Args:
            query: SQL SELECT query string.
            params: Optional tuple of parameters for parameterized queries.
            size: Maximum number of rows to fetch.

        Returns:
            List of dictionaries, each representing a row.

        Raises:
            Exception: If query execution fails.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                rows = cursor.fetchmany(size)
                result = [dict(row) for row in rows]
                self.logger.debug(
                    f"FETCHMANY: {query[:100]}... -> {len(result)} rows (size: {size})"
                )
                return result
        except Exception as e:
            self.logger.error(f"Error fetching many rows '{query[:100]}...': {e}")
            raise

    def begin(self) -> None:
        """Begin a new database transaction.

        Sets autocommit to False to start a transaction. PyMySQL starts
        transactions automatically when autocommit is False.

        Raises:
            Exception: If transaction cannot be started.
        """
        if self._in_transaction:
            self.logger.warning("Transaction already in progress")
            return

        try:
            conn = self._get_connection()
            conn.autocommit(False)
            self._in_transaction = True
            self.logger.debug("Transaction BEGIN")
        except Exception as e:
            self.logger.error(f"Error beginning transaction: {e}")
            raise

    def commit(self) -> None:
        """Commit the current transaction.

        Raises:
            Exception: If commit fails.
        """
        if not self._in_transaction:
            self.logger.warning("No transaction in progress")
            return

        try:
            conn = self._get_connection()
            conn.commit()
            self._in_transaction = False
            self.logger.debug("Transaction COMMIT")
        except Exception as e:
            self.logger.error(f"Error committing transaction: {e}")
            self._in_transaction = False
            raise

    def rollback(self) -> None:
        """Roll back the current transaction.

        Raises:
            Exception: If rollback fails.
        """
        if not self._in_transaction:
            self.logger.warning("No transaction in progress")
            return

        try:
            conn = self._get_connection()
            conn.rollback()
            self._in_transaction = False
            self.logger.debug("Transaction ROLLBACK")
        except Exception as e:
            self.logger.error(f"Error rolling back transaction: {e}")
            self._in_transaction = False
            raise

    def close(self) -> None:
        """Close the database connection.

        Automatically rolls back any pending transaction before closing.
        """
        if self._connection:
            try:
                if self._in_transaction:
                    self.rollback()
                self._connection.close()
                self._connection = None
                self.logger.info("MySQL connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing MySQL connection: {e}")

    def __enter__(self):
        """Context manager entry.

        Returns:
            Self for use in context manager.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit.

        Automatically rolls back transaction on exception and closes connection.

        Args:
            exc_type: Exception type if exception occurred.
            exc_val: Exception value if exception occurred.
            exc_tb: Exception traceback if exception occurred.

        Returns:
            False to allow exceptions to propagate.
        """
        if exc_type is not None and self._in_transaction:
            self.rollback()
        self.close()
        return False
