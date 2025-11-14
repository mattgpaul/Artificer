"""MySQL client for bad ticker tracking."""

import datetime
import os
from typing import Any

from infrastructure.config import MySQLConfig
from infrastructure.mysql.mysql import BaseMySQLClient


class BadTickerClient(BaseMySQLClient):
    """Client for logging and querying bad tickers in MySQL."""

    def __init__(self, config=None) -> None:
        """Initialize bad ticker client.

        Uses shared MySQL database so that bad_tickers table is accessible
        across all components. All algo_trader MySQL clients should use the
        same database to share tables.
        """
        if config is None:
            config = MySQLConfig()
            # Read MySQL connection details from environment variables
            config.host = os.getenv("MYSQL_HOST") or "localhost"
            port_str = os.getenv("MYSQL_PORT") or "3306"
            config.port = int(port_str)
            config.user = os.getenv("MYSQL_USER") or "root"
            config.password = os.getenv("MYSQL_PASSWORD") or ""
            config.database = os.getenv("MYSQL_DATABASE") or "algo_trader"

        super().__init__(config=config)
        self.create_table()
        self.create_missing_tickers_table()

    def create_table(self) -> None:
        """Create bad_tickers table if it doesn't exist."""
        query = """
        CREATE TABLE IF NOT EXISTS bad_tickers (
            ticker VARCHAR(255) PRIMARY KEY,
            timestamp VARCHAR(255) NOT NULL,
            reason TEXT NOT NULL
        )
        """
        try:
            self.execute(query)
            self.logger.info("bad_tickers table created or already exists")
        except Exception as e:
            self.logger.error(f"Error creating bad_tickers table: {e}")
            raise

    def log_bad_ticker(self, ticker: str, timestamp: str, reason: str) -> bool:
        """Log or update a bad ticker record."""
        query = """
        INSERT INTO bad_tickers (ticker, timestamp, reason)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            timestamp = VALUES(timestamp),
            reason = VALUES(reason)
        """
        try:
            self.execute(query, (ticker, timestamp, reason))
            self.logger.debug(f"Logged bad ticker: {ticker} - {reason}")
            return True
        except Exception as e:
            self.logger.error(f"Error logging bad ticker {ticker}: {e}")
            return False

    def get_bad_tickers(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get list of bad tickers ordered by timestamp."""
        query = "SELECT ticker, timestamp, reason FROM bad_tickers ORDER BY timestamp DESC LIMIT %s"
        try:
            results = self.fetchall(query, (limit,))
            return results
        except Exception as e:
            self.logger.error(f"Error fetching bad tickers: {e}")
            return []

    def is_bad_ticker(self, ticker: str) -> bool:
        """Check if a ticker is marked as bad."""
        query = "SELECT 1 FROM bad_tickers WHERE ticker = %s"
        try:
            result = self.fetchone(query, (ticker,))
            return result is not None
        except Exception as e:
            self.logger.error(f"Error checking bad ticker {ticker}: {e}")
            return False

    def remove_bad_ticker(self, ticker: str) -> bool:
        """Remove a ticker from bad_tickers table."""
        query = "DELETE FROM bad_tickers WHERE ticker = %s"
        try:
            self.execute(query, (ticker,))
            self.logger.debug(f"Removed bad ticker: {ticker}")
            return True
        except Exception as e:
            self.logger.error(f"Error removing bad ticker {ticker}: {e}")
            return False

    def create_missing_tickers_table(self) -> None:
        """Create missing_tickers table if it doesn't exist.

        Raises:
            Exception: If table creation fails.
        """
        query = """
        CREATE TABLE IF NOT EXISTS missing_tickers (
            ticker VARCHAR(255) PRIMARY KEY,
            timestamp VARCHAR(255) NOT NULL,
            source VARCHAR(255) NOT NULL
        )
        """
        try:
            self.execute(query)
            self.logger.info("missing_tickers table created or already exists")
        except Exception as e:
            self.logger.error(f"Error creating missing_tickers table: {e}")
            raise

    def store_missing_tickers(self, tickers: list[str], source: str) -> int:
        """Store missing tickers in missing_tickers table.

        Inserts or updates tickers with current timestamp and source. Handles
        duplicates using ON DUPLICATE KEY UPDATE.

        Args:
            tickers: List of ticker symbols to store.
            source: Source identifier for where missing tickers were detected.

        Returns:
            Number of tickers successfully stored.
        """
        timestamp = datetime.datetime.utcnow().isoformat()
        stored_count = 0
        for ticker in tickers:
            query = """
            INSERT INTO missing_tickers (ticker, timestamp, source)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                timestamp = VALUES(timestamp),
                source = VALUES(source)
            """
            try:
                self.execute(query, (ticker, timestamp, source))
                stored_count += 1
            except Exception as e:
                self.logger.error(f"Error storing missing ticker {ticker}: {e}")
        return stored_count

    def get_missing_tickers(self, limit: int = 10000) -> list[str]:
        """Get list of missing tickers ordered by timestamp.

        Args:
            limit: Maximum number of tickers to retrieve. Defaults to 10000.

        Returns:
            List of ticker symbols, or empty list on error.
        """
        query = "SELECT ticker FROM missing_tickers ORDER BY timestamp DESC LIMIT %s"
        try:
            results = self.fetchall(query, (limit,))
            return [r["ticker"] for r in results]
        except Exception as e:
            self.logger.error(f"Error fetching missing tickers: {e}")
            return []

    def clear_missing_tickers(self) -> bool:
        """Clear all entries from missing_tickers table.

        Returns:
            True if operation succeeded, False otherwise.
        """
        query = "DELETE FROM missing_tickers"
        try:
            self.execute(query)
            self.logger.info("Cleared missing_tickers table")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing missing_tickers: {e}")
            return False
