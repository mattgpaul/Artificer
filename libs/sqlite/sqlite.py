"""SQLite database client implementation.

Provides a base client class for SQLite database operations with connection
management, transaction support, and query execution methods.
"""

import sqlite3
from typing import Any

from infrastructure.client import Client
from infrastructure.logging.logger import get_logger


class BaseSQLiteClient(Client):
    """Base SQLite client for database operations.

    Provides connection management, transaction support, and query execution
    methods. Supports both in-memory and file-based SQLite databases.

    Args:
        config: Optional SQLiteConfig instance. If None, creates default config.

    Attributes:
        db_path: Path to SQLite database file.
        timeout: Connection timeout in seconds.
        isolation_level: Transaction isolation level.
        logger: Logger instance for this client.
        _connection: Internal SQLite connection object.
        _in_transaction: Flag indicating if a transaction is in progress.
    """

    def __init__(self, config=None) -> None:
        """Initialize SQLite client with configuration.

        Args:
            config: Optional SQLiteConfig instance. If None, creates default config.
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)

        if config is None:
            from infrastructure.config import SQLiteConfig  # noqa: PLC0415

            config = SQLiteConfig()

        self.db_path = config.db_path
        self.timeout = config.timeout
        self.isolation_level = config.isolation_level

        self._connection: sqlite3.Connection | None = None
        self._in_transaction = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create SQLite connection.

        Returns:
            Active SQLite connection object.
        """
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                isolation_level=self.isolation_level,
            )
            self._connection.row_factory = sqlite3.Row
            self.logger.info(
                f"SQLite connection created: {self.db_path} "
                f"(timeout: {self.timeout}s, isolation: {self.isolation_level})"
            )
        return self._connection

    def ping(self) -> bool:
        """Check if database connection is alive.

        Returns:
            True if connection is active, False otherwise.
        """
        try:
            conn = self._get_connection()
            conn.execute("SELECT 1").fetchone()
            self.logger.debug("SQLite ping successful")
            return True
        except Exception as e:
            self.logger.debug(f"SQLite ping failed: {e}")
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
            cursor = conn.execute(query, params or ())
            conn.commit()
            rowcount = cursor.rowcount
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
            cursor = conn.executemany(query, params_list)
            conn.commit()
            rowcount = cursor.rowcount
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
            cursor = conn.execute(query, params or ())
            row = cursor.fetchone()
            if row:
                result = dict(row)
                self.logger.debug(f"FETCHONE: {query[:100]}... -> 1 row")
                return result
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
            cursor = conn.execute(query, params or ())
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
            cursor = conn.execute(query, params or ())
            rows = cursor.fetchmany(size)
            result = [dict(row) for row in rows]
            self.logger.debug(f"FETCHMANY: {query[:100]}... -> {len(result)} rows (size: {size})")
            return result
        except Exception as e:
            self.logger.error(f"Error fetching many rows '{query[:100]}...': {e}")
            raise

    def begin(self) -> None:
        """Begin a new database transaction.

        Raises:
            Exception: If transaction cannot be started.
        """
        if self._in_transaction:
            self.logger.warning("Transaction already in progress")
            return

        try:
            conn = self._get_connection()
            conn.execute("BEGIN")
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
                self.logger.info("SQLite connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing SQLite connection: {e}")

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
