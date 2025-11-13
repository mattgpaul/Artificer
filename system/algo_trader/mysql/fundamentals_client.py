"""MySQL client for fundamentals data storage.

This module provides database operations for storing and retrieving
company fundamentals static data (sector, industry, entity name, SIC).
"""

import os

from infrastructure.config import MySQLConfig
from infrastructure.mysql.mysql import BaseMySQLClient


class FundamentalsClient(BaseMySQLClient):
    """Client for fundamentals table operations in MySQL.

    Handles creation and upsert operations for company fundamentals static data.
    """

    def __init__(self, config=None) -> None:
        """Initialize FundamentalsClient with MySQL configuration.

        Args:
            config: Optional MySQLConfig instance. If None, creates default config
                with database connection details from environment variables.
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

    def create_table(self) -> None:
        """Create fundamentals table if it doesn't exist.

        Raises:
            Exception: If table creation fails.
        """
        query = """
        CREATE TABLE IF NOT EXISTS fundamentals (
            ticker VARCHAR(255) PRIMARY KEY,
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
        INSERT INTO fundamentals (ticker, sector, industry, entity_name, sic)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            sector = VALUES(sector),
            industry = VALUES(industry),
            entity_name = VALUES(entity_name),
            sic = VALUES(sic)
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

