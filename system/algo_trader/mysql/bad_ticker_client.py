"""MySQL client for bad ticker tracking."""

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
            config.host = os.getenv("MYSQL_HOST", "localhost")
            config.port = int(os.getenv("MYSQL_PORT", "3306"))
            config.user = os.getenv("MYSQL_USER", "root")
            config.password = os.getenv("MYSQL_PASSWORD", "")
            config.database = os.getenv("MYSQL_DATABASE", "algo_trader")

        super().__init__(config=config)
        self.create_table()

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

