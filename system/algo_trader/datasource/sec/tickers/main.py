"""SEC tickers data source.

This module provides functionality to fetch ticker data from SEC APIs
and retrieve company facts data.
"""

import time

import requests

from infrastructure.logging.logger import get_logger
from system.algo_trader.datasource.sec.tickers.dataframe import TickersDataFrameBuilder
from system.algo_trader.datasource.sec.tickers.sic import TickersSICEnricher
from system.algo_trader.datasource.sec.tickers.static import TickersStaticExtractor


class Tickers:
    """SEC tickers data source client.

    Provides methods to fetch ticker registry and company facts data
    from SEC APIs with caching support.
    """

    def __init__(self):
        """Initialize SEC tickers client."""
        self.logger = get_logger(self.__class__.__name__)
        self._ticker_to_cik_cache: dict[str, str] = {}
        self._company_facts_cache: dict[str, tuple[dict, float]] = {}
        self._dataframe_builder = TickersDataFrameBuilder(logger=self.logger)
        self._static_extractor = TickersStaticExtractor(logger=self.logger)
        self._sic_enricher = TickersSICEnricher(logger=self.logger)

    def get_tickers(self):
        """Fetch all tickers from SEC company tickers registry.

        Returns:
            Dictionary mapping ticker data, or None if fetch fails.
        """
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            headers = {
                "User-Agent": "Company Name company@email.com",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            }
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                self.logger.error(f"Failed to get tickers: HTTP {response.status_code}")
                self.logger.info(f"Response: {response.text[:500]}")
                return None

            content_type = response.headers.get("Content-Type", "")
            if "json" not in content_type.lower():
                self.logger.error(f"Response is not JSON. Content-Type: {content_type}")
                self.logger.info(f"Response: {response.text[:500]}")
                return None

            data = response.json()
            return data
        except Exception as e:
            self.logger.error(f"Failed to get tickers: {e}")
            return None

    def _get_cik_from_ticker(self, ticker: str) -> str | None:
        if ticker in self._ticker_to_cik_cache:
            return self._ticker_to_cik_cache[ticker]

        tickers_data = self.get_tickers()
        if not tickers_data:
            return None

        for _key, value in tickers_data.items():
            if isinstance(value, dict) and value.get("ticker") == ticker.upper():
                cik_str = str(value.get("cik_str", ""))
                cik_padded = cik_str.zfill(10)
                self._ticker_to_cik_cache[ticker.upper()] = cik_padded
                return cik_padded

        self.logger.error(f"Ticker {ticker} not found in SEC registry")
        return None

    def _fetch_company_facts(self, cik: str, use_cache: bool = True) -> dict | None:
        if use_cache and cik in self._company_facts_cache:
            facts_dict, cache_timestamp = self._company_facts_cache[cik]
            cache_age_hours = (time.time() - cache_timestamp) / 3600
            if cache_age_hours < 24:
                self.logger.debug(f"Using cached company facts for CIK {cik}")
                return facts_dict

        try:
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            headers = {
                "User-Agent": "Company Name company@email.com",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            }
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                self.logger.error(f"Failed to get company facts: HTTP {response.status_code}")
                return None

            content_type = response.headers.get("Content-Type", "")
            if "json" not in content_type.lower():
                self.logger.error(f"Response is not JSON. Content-Type: {content_type}")
                return None

            data = response.json()
            self._company_facts_cache[cik] = (data, time.time())
            return data
        except Exception as e:
            self.logger.error(f"Failed to get company facts: {e}")
            return None

    def get_company_facts(self, ticker: str, years_back: int = 10) -> dict | None:
        """Fetch company facts data for a ticker.

        Args:
            ticker: Ticker symbol to fetch facts for.
            years_back: Number of years to look back for data. Default: 10.

        Returns:
            Dictionary containing company facts data, or None if fetch fails.
        """
        cik = self._get_cik_from_ticker(ticker)
        if not cik:
            return None

        facts = self._fetch_company_facts(cik)
        if not facts:
            return None

        static_info = self._static_extractor.extract_static_info(facts, ticker.upper())

        tickers_data = self.get_tickers()
        static_info = self._sic_enricher.enrich_static_info(
            static_info, cik, ticker.upper(), tickers_data
        )

        time_series_df = self._dataframe_builder.build_time_series_dataframe(
            facts, ticker.upper(), years_back
        )

        return {"static": static_info, "time_series": time_series_df}
