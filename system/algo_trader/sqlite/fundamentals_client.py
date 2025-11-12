import os

from infrastructure.config import SQLiteConfig
from infrastructure.sqlite.sqlite import BaseSQLiteClient


class FundamentalsClient(BaseSQLiteClient):
    def __init__(self, config=None) -> None:
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

