"""Static information extractor for SEC tickers data.

This module provides functionality to extract static company information
from SEC company facts data.
"""

from infrastructure.logging.logger import get_logger


class TickersStaticExtractor:
    """Extractor for static company information.

    Extracts static information like entity name, sector, industry, and
    SIC code from SEC company facts data.
    """

    def __init__(self, logger=None):
        """Initialize static extractor.

        Args:
            logger: Optional logger instance. If not provided, creates a new one.
        """
        self.logger = logger or get_logger(self.__class__.__name__)

    def extract_static_info(self, facts: dict, ticker: str) -> dict[str, str | None]:
        """Extract static company information from facts data.

        Args:
            facts: Company facts dictionary from SEC API.
            ticker: Ticker symbol.

        Returns:
            Dictionary containing ticker, sector, industry, entity_name, and sic.
        """
        entity_name = facts.get("entityName")
        if isinstance(entity_name, dict):
            entity_name = entity_name.get("name", entity_name)
        elif not isinstance(entity_name, str):
            entity_name = None

        sic = facts.get("sic")
        sic_description = facts.get("sicDescription")

        sector = None
        industry = sic_description

        if "sector" in facts:
            sector = facts.get("sector")
        if "industry" in facts:
            industry = facts.get("industry") or sic_description
        if isinstance(entity_name, dict):
            if "sector" in entity_name:
                sector = entity_name.get("sector")
            if "industry" in entity_name:
                industry = entity_name.get("industry") or sic_description

        return {
            "ticker": ticker,
            "sector": sector,
            "industry": industry,
            "entity_name": entity_name,
            "sic": str(sic) if sic else None,
        }

    def get_ticker_data_from_registry(self, tickers_data: dict, ticker: str) -> dict | None:
        """Get ticker data from SEC tickers registry.

        Args:
            tickers_data: Dictionary containing ticker registry data.
            ticker: Ticker symbol to look up.

        Returns:
            Dictionary containing ticker data if found, None otherwise.
        """
        if not tickers_data:
            return None

        for _key, value in tickers_data.items():
            if isinstance(value, dict) and value.get("ticker") == ticker:
                return value

        return None
