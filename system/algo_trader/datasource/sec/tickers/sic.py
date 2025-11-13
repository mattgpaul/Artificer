"""SIC code enricher for SEC tickers data.

This module provides functionality to derive sector and industry information
from SIC codes and SEC submission data.
"""

import requests

from infrastructure.logging.logger import get_logger


class TickersSICEnricher:
    """Enricher for SIC-based sector and industry data.

    Derives sector and industry information from SIC codes and enriches
    ticker data with this information.
    """

    def __init__(self, logger=None):
        """Initialize SIC enricher.

        Args:
            logger: Optional logger instance. If not provided, creates a new one.
        """
        self.logger = logger or get_logger(self.__class__.__name__)

    def derive_sector_from_sic(self, sic: str) -> str | None:
        """Derive sector name from SIC code.

        Args:
            sic: SIC code as string.

        Returns:
            Sector name if SIC code matches known ranges, None otherwise.
        """
        if not sic or not isinstance(sic, str):
            return None

        try:
            sic_code = int(sic)
        except (ValueError, TypeError):
            return None

        sic_ranges = {
            (100, 999): "Agriculture, Forestry, Fishing",
            (1000, 1499): "Mining",
            (1500, 1799): "Construction",
            (2000, 2099): "Manufacturing - Food & Kindred Products",
            (2100, 2199): "Manufacturing - Tobacco Products",
            (2200, 2299): "Manufacturing - Textile Mill Products",
            (2300, 2399): "Manufacturing - Apparel & Other Textile Products",
            (2400, 2499): "Manufacturing - Lumber & Wood Products",
            (2500, 2599): "Manufacturing - Furniture & Fixtures",
            (2600, 2699): "Manufacturing - Paper & Allied Products",
            (2700, 2799): "Manufacturing - Printing & Publishing",
            (2800, 2899): "Manufacturing - Chemicals & Allied Products",
            (2900, 2999): "Manufacturing - Petroleum & Coal Products",
            (3000, 3099): "Manufacturing - Rubber & Plastic Products",
            (3100, 3199): "Manufacturing - Leather Products",
            (3200, 3299): "Manufacturing - Stone, Clay & Glass Products",
            (3300, 3399): "Manufacturing - Primary Metal Industries",
            (3400, 3499): "Manufacturing - Fabricated Metal Products",
            (3500, 3599): "Manufacturing - Industrial Machinery & Equipment",
            (3600, 3699): "Manufacturing - Electronic & Electrical Equipment",
            (3700, 3799): "Manufacturing - Transportation Equipment",
            (3800, 3899): "Manufacturing - Instruments & Related Products",
            (3900, 3999): "Manufacturing - Miscellaneous",
            (4000, 4099): "Transportation",
            (4100, 4199): "Transportation",
            (4200, 4299): "Transportation",
            (4300, 4399): "Transportation",
            (4400, 4499): "Transportation",
            (4500, 4599): "Transportation",
            (4600, 4699): "Transportation",
            (4700, 4799): "Transportation",
            (4800, 4899): "Communications",
            (4900, 4999): "Utilities",
            (5000, 5099): "Wholesale Trade",
            (5100, 5199): "Wholesale Trade",
            (5200, 5299): "Retail Trade",
            (5300, 5399): "Retail Trade",
            (5400, 5499): "Retail Trade",
            (5500, 5599): "Retail Trade",
            (5600, 5699): "Retail Trade",
            (5700, 5799): "Retail Trade",
            (5800, 5899): "Retail Trade",
            (5900, 5999): "Retail Trade",
            (6000, 6099): "Finance, Insurance, Real Estate",
            (6100, 6199): "Finance, Insurance, Real Estate",
            (6200, 6299): "Finance, Insurance, Real Estate",
            (6300, 6399): "Finance, Insurance, Real Estate",
            (6400, 6499): "Finance, Insurance, Real Estate",
            (6500, 6599): "Finance, Insurance, Real Estate",
            (6600, 6699): "Finance, Insurance, Real Estate",
            (6700, 6799): "Finance, Insurance, Real Estate",
            (7000, 7099): "Services",
            (7100, 7199): "Services",
            (7200, 7299): "Services",
            (7300, 7399): "Services",
            (7400, 7499): "Services",
            (7500, 7599): "Services",
            (7600, 7699): "Services",
            (7700, 7799): "Services",
            (7800, 7899): "Services",
            (7900, 7999): "Services",
            (8000, 8099): "Services",
            (8100, 8199): "Services",
            (8200, 8299): "Services",
            (8300, 8399): "Services",
            (8400, 8499): "Services",
            (8500, 8599): "Services",
            (8600, 8699): "Services",
            (8700, 8799): "Services",
            (8800, 8899): "Services",
            (8900, 8999): "Services",
            (9000, 9099): "Public Administration",
            (9100, 9199): "Public Administration",
            (9200, 9299): "Public Administration",
            (9300, 9399): "Public Administration",
            (9400, 9499): "Public Administration",
            (9500, 9599): "Public Administration",
            (9600, 9699): "Public Administration",
            (9700, 9799): "Public Administration",
            (9800, 9899): "Nonclassifiable",
            (9900, 9999): "Nonclassifiable",
        }

        for (start, end), sector in sic_ranges.items():
            if start <= sic_code <= end:
                return sector

        return None

    def fetch_sic_info(self, cik: str) -> dict | None:
        """Fetch SIC information from SEC submissions API.

        Args:
            cik: Central Index Key (CIK) for the company.

        Returns:
            Dictionary containing SIC information, or None if fetch fails.
        """
        try:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            headers = {
                "User-Agent": "Company Name company@email.com",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            }
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                return None

            data = response.json()

            sic_info = {}
            if "sic" in data:
                sic_info["sic"] = data.get("sic")
            if "sicDescription" in data:
                sic_info["sicDescription"] = data.get("sicDescription")
            if "industry" in data:
                sic_info["industry"] = data.get("industry")
            if "sector" in data:
                sic_info["sector"] = data.get("sector")

            return sic_info if sic_info else None
        except Exception:
            return None

    def enrich_static_info(  # noqa: PLR0912
        self, static_info: dict, cik: str, ticker: str, tickers_data: dict | None
    ) -> dict:
        """Enrich static info with SIC-derived sector and industry.

        Args:
            static_info: Dictionary containing static company information.
            cik: Central Index Key (CIK) for the company.
            ticker: Ticker symbol.
            tickers_data: Optional ticker registry data.

        Returns:
            Enriched static info dictionary with sector and industry.
        """
        if not static_info.get("sector") or not static_info.get("industry"):
            if tickers_data:
                ticker_data = self.get_ticker_data_from_registry(tickers_data, ticker)
                if ticker_data:
                    if not static_info.get("sector") and "sector" in ticker_data:
                        static_info["sector"] = ticker_data.get("sector")
                    if not static_info.get("industry") and "industry" in ticker_data:
                        static_info["industry"] = ticker_data.get("industry")

        if (
            not static_info.get("sic")
            or not static_info.get("industry")
            or not static_info.get("sector")
        ):
            sic_info = self.fetch_sic_info(cik)
            if sic_info:
                if not static_info.get("sic") and sic_info.get("sic"):
                    static_info["sic"] = sic_info.get("sic")
                if not static_info.get("industry"):
                    industry = sic_info.get("sicDescription") or sic_info.get("industry")
                    if industry:
                        static_info["industry"] = industry
                if not static_info.get("sector") and sic_info.get("sector"):
                    static_info["sector"] = sic_info.get("sector")

        if not static_info.get("sector") and static_info.get("sic"):
            derived_sector = self.derive_sector_from_sic(static_info.get("sic"))
            if derived_sector:
                static_info["sector"] = derived_sector

        return static_info

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
