"""SQLite client for bad ticker tracking."""

import os
from typing import Any

from infrastructure.config import SQLiteConfig
from infrastructure.sqlite.sqlite import BaseSQLiteClient


class BadTickerClient(BaseSQLiteClient):
    """Client for logging and querying bad tickers in SQLite."""

    def __init__(self, config=None) -> None:
        """Initialize bad ticker client."""
        if config is None:
            config = SQLiteConfig()
            db_path_env = os.getenv("SQLITE_DB_PATH")
            if db_path_env:
                config.db_path = db_path_env
        super().__init__(config=config)
        self.create_table()

    def create_table(self) -> None:
        """Create bad_tickers table if it doesn't exist."""
        query = """
        CREATE TABLE IF NOT EXISTS bad_tickers (
            ticker TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
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
        INSERT OR REPLACE INTO bad_tickers (ticker, timestamp, reason)
        VALUES (?, ?, ?)
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
        query = "SELECT ticker, timestamp, reason FROM bad_tickers ORDER BY timestamp DESC LIMIT ?"
        try:
            results = self.fetchall(query, (limit,))
            return results
        except Exception as e:
            self.logger.error(f"Error fetching bad tickers: {e}")
            return []

    def is_bad_ticker(self, ticker: str) -> bool:
        """Check if a ticker is marked as bad."""
        query = "SELECT 1 FROM bad_tickers WHERE ticker = ?"
        try:
            result = self.fetchone(query, (ticker,))
            return result is not None
        except Exception as e:
            self.logger.error(f"Error checking bad ticker {ticker}: {e}")
            return False
