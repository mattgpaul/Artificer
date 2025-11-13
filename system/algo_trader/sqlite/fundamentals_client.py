"""SQLite client for fundamentals data storage.

This module provides database operations for storing and retrieving
company fundamentals static data (sector, industry, entity name, SIC).
"""

import os

from infrastructure.config import SQLiteConfig
from infrastructure.sqlite.sqlite import BaseSQLiteClient


class FundamentalsClient(BaseSQLiteClient):
    """Client for fundamentals table operations in SQLite.

    Handles creation and upsert operations for company fundamentals static data.
    """

    def __init__(self, config=None) -> None:
        """Initialize FundamentalsClient with SQLite configuration.

        Args:
            config: Optional SQLiteConfig instance. If None, creates default config
                with database path from environment or default location.
        """
        if config is None:
            config = SQLiteConfig()
            db_path_env = os.getenv("SQLITE_DB_PATH")
            if db_path_env:
                config.db_path = db_path_env
            else:
                config.db_path = "./data/algo_trader.db"

            if config.db_path != ":memory:":
                db_dir = os.path.dirname(os.path.abspath(config.db_path))
                if db_dir:
                    os.makedirs(db_dir, exist_ok=True)

        super().__init__(config=config)
        self.create_table()

    def create_table(self) -> None:
        """Create fundamentals table if it doesn't exist.

        Raises:
            Exception: If table creation fails.
        """
        query = """
        CREATE TABLE IF NOT EXISTS fundamentals (
            ticker TEXT PRIMARY KEY,
            sector TEXT,
            industry TEXT,
            entity_name TEXT,
            sic TEXT
        )
        """
        try:
            self.execute(query)
            self.logger.info("fundamentals table created or already exists")
        except Exception as e:
            self.logger.error(f"Error creating fundamentals table: {e}")
            raise

    def upsert_fundamentals(self, static_data: dict) -> bool:
        """Upsert fundamentals data for a ticker.

        Args:
            static_data: Dictionary containing ticker, sector, industry,
                entity_name, and sic fields.

        Returns:
            True if upsert succeeded, False otherwise.
        """
        query = """
        INSERT OR REPLACE INTO fundamentals (ticker, sector, industry, entity_name, sic)
        VALUES (?, ?, ?, ?, ?)
        """
        try:
            self.execute(
                query,
                (
                    static_data.get("ticker"),
                    static_data.get("sector"),
                    static_data.get("industry"),
                    static_data.get("entity_name"),
                    static_data.get("sic"),
                ),
            )
            self.logger.debug(f"Upserted fundamentals for ticker: {static_data.get('ticker')}")
            return True
        except Exception as e:
            self.logger.error(f"Error upserting fundamentals: {e}")
            return False
