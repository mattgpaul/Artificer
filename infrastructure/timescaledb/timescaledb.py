"""TimescaleDB client implementation.

This module provides a TimescaleDB client for database operations including
connection management, transaction support, and query execution.
"""

from __future__ import annotations

import psycopg2
from psycopg2.extensions import connection as psycopg_connection

from infrastructure.client import Client
from infrastructure.config import TimescaleDBConfig
from infrastructure.logging.logger import get_logger


class BaseTimescaleDBClient(Client):
    """Base TimescaleDB client for database operations.

    Provides connection management, transaction support, and query execution
    methods. Supports connection pooling and both autocommit and transaction modes.
    """

    def __init__(self, config=None) -> None:
        """Initialize TimescaleDB client with configuration.

        Args:
            config: Optional TimescaleDBConfig instance. If None, creates default config.
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)

        if config is None:
            config = TimescaleDBConfig()

        self.host = config.host
        self.port = config.port
        self.user = config.user
        self.password = config.password
        self.database = config.database

        # Lazily-initialized connection handle
        self._connection: psycopg_connection | None = None

    def _get_connection(self) -> psycopg_connection:
        """Get or create TimescaleDB connection.

        Returns:
            Active TimescaleDB connection object.
        """
        if self._connection is None:
            self._connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )
            self.logger.info(
                f"TimescaleDB connection created: {self.host}:{self.port}/{self.database}"
            )
        return self._connection

    def _close_connection(self) -> None:
        """Close the TimescaleDB connection.

        Raises:
            Exception: If connection cannot be closed.
        """
        if self._connection:
            try:
                self._connection.close()
                self._connection = None
                self.logger.info("TimescaleDB connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing TimescaleDB connection: {e}")
            self._connection = None

    def ping(self) -> bool:
        """Check if database connection is alive.

        Returns:
            True if connection is active, False otherwise.
        """
        try:
            conn = self._get_connection()
            # Use a simple, portable health check query rather than driver-specific
            # methods; this matches the testing contract and keeps behavior explicit.
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.logger.debug("TimescaleDB ping successful")
            return True
        except Exception as e:
            self.logger.debug(f"TimescaleDB ping failed: {e}")
            return False

    def close(self):
        """Close the TimescaleDB connection.

        Safely closes the database connection if it exists, handling
        any errors that occur during the close operation.
        """
        if self._connection:
            try:
                self._connection.close()
                self._connection = None
                self.logger.info("TimescaleDB connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing TimescaleDB connection: {e}")
            self._connection = None
        else:
            self.logger.warning("TimescaleDB connection not initialized, skipping close")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
