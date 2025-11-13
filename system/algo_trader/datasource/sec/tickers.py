"""SEC ticker data retrieval module."""

import time
from datetime import datetime, timezone

import pandas as pd
import requests

from infrastructure.logging.logger import get_logger
from system.algo_trader.datasource.sec.company_facts_config import load_company_facts_config


class Tickers:
    """Class for retrieving ticker data from SEC.gov."""

    METRICS_CONFIG: dict[str, dict] = load_company_facts_config()

    def __init__(self):
        """Initialize Tickers with a logger."""
        self.logger = get_logger(self.__class__.__name__)
        self._ticker_to_cik_cache: dict[str, str] = {}
        self._company_facts_cache: dict[str, tuple[dict, float]] = {}

    def get_tickers(self):
        """Retrieve ticker data from SEC.gov company_tickers.json.

        Returns:
            Dictionary of ticker data from SEC.gov, or None on error.
        """
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            headers = {
                "User-Agent": "Company Name company@email.com",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            }
            response = requests.get(url, headers=headers)

            # Check if response is successful and is JSON
            if response.status_code != 200:
                self.logger.error(f"Failed to get tickers: HTTP {response.status_code}")
                self.logger.info(f"Response: {response.text[:500]}")
                return None

            # Check if the response is actually JSON
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

    def _validate_fact_exists(self, facts_data: dict, namespace: str, fact_name: str) -> bool:
        """Validate that namespace and fact exist in facts data.

        Args:
            facts_data: The facts data dictionary.
            namespace: The namespace to check.
            fact_name: The fact name to check.

        Returns:
            True if both namespace and fact exist, False otherwise.
        """
        if namespace not in facts_data:
            self.logger.debug(f"Namespace {namespace} not found in facts")
            available_namespaces = list(facts_data.keys())
            self.logger.debug(f"Available namespaces: {available_namespaces}")
            return False

        if fact_name not in facts_data[namespace]:
            self.logger.debug(f"Fact {fact_name} not found in namespace {namespace}")
            available_facts = list(facts_data[namespace].keys())[:20]
            self.logger.debug(f"Available facts in {namespace}: {available_facts}")
            if "EntityCommonStock" in fact_name or "Shares" in fact_name:
                matching_facts = [
                    f
                    for f in facts_data[namespace].keys()
                    if "share" in f.lower() or "stock" in f.lower() or "outstanding" in f.lower()
                ]
                if matching_facts:
                    self.logger.debug(f"Found similar facts in {namespace}: {matching_facts[:10]}")
            return False

        return True

    def _unit_matches_preference(self, unit: str, unit_preference: list[str]) -> bool:
        """Check if a unit matches the preference list.

        Args:
            unit: The unit name to check.
            unit_preference: List of preferred unit names.

        Returns:
            True if unit matches any preference, False otherwise.
        """
        if not unit_preference:
            return True

        unit_lower = unit.lower()
        matched = any(
            pref.lower() in unit_lower or unit_lower in pref.lower() for pref in unit_preference
        )
        if not matched:
            self.logger.debug(f"Unit {unit} does not match preference {unit_preference}")
        return matched

    def _parse_period(
        self, period_info: dict, require_quarterly: bool, cutoff_date: datetime
    ) -> dict | None:
        """Parse and validate a single period from unit data.

        Args:
            period_info: Dictionary containing period information.
            require_quarterly: Whether to require quarterly periods only.
            cutoff_date: Minimum date for periods to include.

        Returns:
            Dictionary with period data if valid, None otherwise.
        """
        period_end_str = period_info.get("end", "")
        if not period_end_str:
            return None

        if require_quarterly:
            fp = period_info.get("fp", "")
            if fp not in ["Q1", "Q2", "Q3", "Q4"]:
                return None

        try:
            period_end = datetime.fromisoformat(period_end_str.replace("Z", "+00:00"))
            if period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            return None

        if period_end < cutoff_date:
            return None

        value = period_info.get("val")
        if value is None:
            return None

        datetime_ms = int(period_end.timestamp() * 1000)

        return {
            "value": value,
            "period_end": period_end_str,
            "datetime": datetime_ms,
        }

    def _extract_periods_for_single_fact(
        self,
        facts_data: dict,
        namespace: str,
        fact_name: str,
        unit_preference: list[str],
        years_back: int,
        require_quarterly: bool,
    ) -> list[dict]:
        """Extract periods for a single fact name.

        Helper method to extract periods for a specific fact name.

        Args:
            facts_data: The facts data dictionary.
            namespace: The namespace to check.
            fact_name: Name of the fact to extract.
            unit_preference: List of preferred unit names.
            years_back: Number of years back to include data.
            require_quarterly: Whether to require quarterly periods only.

        Returns:
            List of dictionaries containing period data with value, period_end, datetime, and unit.
        """
        periods = []

        if not self._validate_fact_exists(facts_data, namespace, fact_name):
            return periods

        fact_data = facts_data[namespace][fact_name]
        units = fact_data.get("units", {})

        if not units:
            self.logger.debug(f"No units found for fact {fact_name}")
            return periods

        self.logger.debug(f"Available units for {fact_name}: {list(units.keys())}")

        cutoff_date = datetime.now(timezone.utc).replace(
            year=datetime.now(timezone.utc).year - years_back
        )

        for unit, unit_data in units.items():
            if not self._unit_matches_preference(unit, unit_preference):
                continue

            for period_info in unit_data:
                period = self._parse_period(period_info, require_quarterly, cutoff_date)
                if period:
                    period["unit"] = unit
                    periods.append(period)

        return periods

    def _extract_all_periods_for_fact(
        self, facts: dict, fact_name: str, years_back: int = 10, require_quarterly: bool = True
    ) -> list[dict]:
        """Extract all periods for a given fact from company facts data.

        If the primary fact name is not found or has no valid periods, tries alternative
        fact names from the configuration in order until one with valid periods is found.

        Args:
            facts: Company facts dictionary from SEC API.
            fact_name: Name of the fact to extract.
            years_back: Number of years back to include data.
            require_quarterly: Whether to require quarterly periods only.

        Returns:
            List of dictionaries containing period data with value, period_end, datetime, and unit.
        """
        facts_data = facts.get("facts", {})
        config = self.METRICS_CONFIG.get(fact_name, {})
        namespace = config.get("namespace", "us-gaap")
        unit_preference = config.get("unit_preference", [])
        alternatives = config.get("alternatives", [])

        # Try primary fact name first
        periods = self._extract_periods_for_single_fact(
            facts_data, namespace, fact_name, unit_preference, years_back, require_quarterly
        )

        # If primary fact yielded no periods and alternatives exist, try alternatives
        if not periods and alternatives:
            self.logger.info(
                f"Fact {fact_name} has no valid periods in namespace {namespace}, trying alternatives: {alternatives}"
            )
            self.logger.debug(
                f"Fact {fact_name} has no valid periods in namespace {namespace}, trying alternatives: {alternatives}"
            )

            for alt_fact_name in alternatives:
                alt_periods = self._extract_periods_for_single_fact(
                    facts_data,
                    namespace,
                    alt_fact_name,
                    unit_preference,
                    years_back,
                    require_quarterly,
                )
                if alt_periods:
                    periods = alt_periods
                    self.logger.info(
                        f"Using alternative fact name '{alt_fact_name}' instead of '{fact_name}' "
                        f"(found {len(periods)} periods)"
                    )
                    self.logger.debug(
                        f"Using alternative fact name '{alt_fact_name}' instead of '{fact_name}' "
                        f"(found {len(periods)} periods)"
                    )
                    break

            if not periods:
                self.logger.debug(
                    f"Fact {fact_name} and all alternatives {alternatives} yielded no valid periods "
                    f"in namespace {namespace}"
                )

        return periods

    def _build_time_series_dataframe(  # noqa: C901, PLR0912
        self, facts: dict, ticker: str, years_back: int = 10
    ) -> pd.DataFrame:
        all_data = {}
        shares_outstanding_data = {}
        market_cap_data = {}

        for fact_name, config in self.METRICS_CONFIG.items():
            column_name = config["column"]
            # EntityCommonStockSharesOutstanding and EntityPublicFloat are annual, not quarterly
            require_quarterly = fact_name not in [
                "EntityCommonStockSharesOutstanding",
                "EntityPublicFloat",
            ]
            periods = self._extract_all_periods_for_fact(
                facts, fact_name, years_back, require_quarterly
            )

            if fact_name == "EntityCommonStockSharesOutstanding":
                for period in periods:
                    datetime_ms = period["datetime"]
                    shares_outstanding_data[datetime_ms] = period["value"]
            elif fact_name == "EntityPublicFloat":
                for period in periods:
                    datetime_ms = period["datetime"]
                    market_cap_data[datetime_ms] = period["value"]
            else:
                for period in periods:
                    datetime_ms = period["datetime"]
                    if datetime_ms not in all_data:
                        all_data[datetime_ms] = {"ticker": ticker}
                    all_data[datetime_ms][column_name] = period["value"]

        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame.from_dict(all_data, orient="index")
        df.index = pd.to_datetime(df.index, unit="ms", utc=True)
        df = df.sort_index()
        df["ticker"] = ticker

        if shares_outstanding_data:
            shares_df = pd.DataFrame.from_dict(
                {
                    "datetime_ms": list(shares_outstanding_data.keys()),
                    "shares": list(shares_outstanding_data.values()),
                }
            )
            shares_df["datetime"] = pd.to_datetime(shares_df["datetime_ms"], unit="ms", utc=True)

            for idx in df.index:
                closest_shares = shares_df.loc[
                    (shares_df["datetime"] <= idx)
                    & (shares_df["datetime"] >= idx - pd.Timedelta(days=30))
                ]
                if len(closest_shares) > 0:
                    df.loc[idx, "shares_outstanding"] = closest_shares.iloc[-1]["shares"]
                else:
                    closest_shares = shares_df.loc[shares_df["datetime"] <= idx]
                    if len(closest_shares) > 0:
                        df.loc[idx, "shares_outstanding"] = closest_shares.iloc[-1]["shares"]

        # Handle EntityPublicFloat (market_cap) - annual data forward-filled to quarterly periods
        if market_cap_data:
            market_cap_df = pd.DataFrame.from_dict(
                {
                    "datetime_ms": list(market_cap_data.keys()),
                    "market_cap": list(market_cap_data.values()),
                }
            )
            market_cap_df["datetime"] = pd.to_datetime(
                market_cap_df["datetime_ms"], unit="ms", utc=True
            )
            market_cap_df = market_cap_df.set_index("datetime")
            market_cap_df = market_cap_df.sort_index()

            # Initialize market_cap column in main DataFrame as float64
            df["market_cap"] = pd.NA

            # Map annual market_cap values to quarterly periods
            for idx in df.index:
                # Find the most recent market_cap value on or before this quarterly period
                market_cap_on_or_before = market_cap_df[market_cap_df.index <= idx]
                if not market_cap_on_or_before.empty:
                    df.loc[idx, "market_cap"] = float(
                        market_cap_on_or_before["market_cap"].iloc[-1]
                    )

            # Convert to numeric and forward-fill market_cap to handle any gaps
            df["market_cap"] = pd.to_numeric(df["market_cap"], errors="coerce")
            df["market_cap"] = df["market_cap"].ffill()
        else:
            # Initialize market_cap column even if no data available
            df["market_cap"] = pd.NA

        return df

    def _extract_static_info(self, facts: dict, ticker: str) -> dict[str, str | None]:
        entity_name = facts.get("entityName")
        if isinstance(entity_name, dict):
            entity_name = entity_name.get("name", entity_name)
        elif not isinstance(entity_name, str):
            entity_name = None

        sic = facts.get("sic")
        sic_description = facts.get("sicDescription")
        
        sector = None
        industry = sic_description
        
        self.logger.debug(f"{ticker}: Extracting static info from company facts API")
        self.logger.debug(f"{ticker}: Top-level keys available: {list(facts.keys())}")
        
        if "sector" in facts:
            sector = facts.get("sector")
            self.logger.debug(f"{ticker}: Found sector in top-level facts: {sector}")
        if "industry" in facts:
            industry = facts.get("industry") or sic_description
            self.logger.debug(f"{ticker}: Found industry in top-level facts: {industry}")
        if isinstance(entity_name, dict):
            self.logger.debug(f"{ticker}: entityName is dict with keys: {list(entity_name.keys())}")
            if "sector" in entity_name:
                sector = entity_name.get("sector")
                self.logger.debug(f"{ticker}: Found sector in entityName: {sector}")
            if "industry" in entity_name:
                industry = entity_name.get("industry") or sic_description
                self.logger.debug(f"{ticker}: Found industry in entityName: {industry}")
        
        self.logger.debug(f"{ticker}: Initial extraction - sector: {sector}, industry: {industry}, sic: {sic}, sicDescription: {sic_description}")

        return {
            "ticker": ticker,
            "sector": sector,
            "industry": industry,
            "entity_name": entity_name,
            "sic": str(sic) if sic else None,
        }

    def get_company_facts(self, ticker: str, years_back: int = 10) -> dict | None:
        """Retrieve company facts data for a given ticker.

        Fetches company facts from SEC API and processes them into static
        information and time series DataFrame.

        Args:
            ticker: Stock ticker symbol to retrieve facts for.
            years_back: Number of years back to include data. Default: 10.

        Returns:
            Dictionary with 'static' and 'time_series' keys, or None if data
            cannot be retrieved. The 'static' key contains company metadata,
            and 'time_series' contains a DataFrame with financial metrics.
        """
        cik = self._get_cik_from_ticker(ticker)
        if not cik:
            return None

        facts = self._fetch_company_facts(cik)
        if not facts:
            return None

        static_info = self._extract_static_info(facts, ticker.upper())
        
        # Try to enrich with ticker registry data if sector/industry missing
        if not static_info.get("sector") or not static_info.get("industry"):
            self.logger.debug(f"{ticker}: Checking ticker registry for sector/industry")
            ticker_data = self._get_ticker_data_from_registry(ticker.upper())
            if ticker_data:
                self.logger.debug(f"{ticker}: Ticker registry data keys: {list(ticker_data.keys())}")
                if not static_info.get("sector") and "sector" in ticker_data:
                    static_info["sector"] = ticker_data.get("sector")
                    self.logger.debug(f"{ticker}: Added sector from registry: {static_info['sector']}")
                if not static_info.get("industry") and "industry" in ticker_data:
                    static_info["industry"] = ticker_data.get("industry")
                    self.logger.debug(f"{ticker}: Added industry from registry: {static_info['industry']}")
            else:
                self.logger.debug(f"{ticker}: No ticker registry data found")
        
        # Try to fetch SIC code and sector/industry from SEC company metadata API
        if not static_info.get("sic") or not static_info.get("industry") or not static_info.get("sector"):
            self.logger.debug(f"{ticker}: Fetching SIC/industry from SEC submissions API (CIK: {cik})")
            sic_info = self._fetch_sic_info(cik)
            if sic_info:
                self.logger.debug(f"{ticker}: Submissions API returned: {sic_info}")
                if not static_info.get("sic") and sic_info.get("sic"):
                    static_info["sic"] = sic_info.get("sic")
                    self.logger.debug(f"{ticker}: Added SIC from submissions API: {static_info['sic']}")
                if not static_info.get("industry"):
                    industry = sic_info.get("sicDescription") or sic_info.get("industry")
                    if industry:
                        static_info["industry"] = industry
                        self.logger.debug(f"{ticker}: Added industry from submissions API: {static_info['industry']}")
                if not static_info.get("sector") and sic_info.get("sector"):
                    static_info["sector"] = sic_info.get("sector")
                    self.logger.debug(f"{ticker}: Added sector from submissions API: {static_info['sector']}")
            else:
                self.logger.debug(f"{ticker}: No SIC info found in submissions API")
        
        # Derive sector from SIC code if still missing
        if not static_info.get("sector") and static_info.get("sic"):
            self.logger.debug(f"{ticker}: Deriving sector from SIC code: {static_info.get('sic')}")
            derived_sector = self._derive_sector_from_sic(static_info.get("sic"))
            if derived_sector:
                static_info["sector"] = derived_sector
                self.logger.debug(f"{ticker}: Derived sector from SIC: {static_info['sector']}")
            else:
                self.logger.debug(f"{ticker}: Could not derive sector from SIC code")
        
        self.logger.debug(f"{ticker}: Final static info - sector: {static_info.get('sector')}, industry: {static_info.get('industry')}, sic: {static_info.get('sic')}, entity_name: {static_info.get('entity_name')}")
        
        time_series_df = self._build_time_series_dataframe(facts, ticker.upper(), years_back)

        return {"static": static_info, "time_series": time_series_df}
    
    def _get_ticker_data_from_registry(self, ticker: str) -> dict | None:
        tickers_data = self.get_tickers()
        if not tickers_data:
            return None
        
        for _key, value in tickers_data.items():
            if isinstance(value, dict) and value.get("ticker") == ticker:
                return value
        
        return None
    
    def _derive_sector_from_sic(self, sic: str) -> str | None:
        if not sic or not isinstance(sic, str):
            self.logger.debug(f"Invalid SIC code for sector derivation: {sic}")
            return None
        
        try:
            sic_code = int(sic)
            self.logger.debug(f"Deriving sector from SIC code: {sic_code}")
        except (ValueError, TypeError):
            self.logger.debug(f"Could not convert SIC to integer: {sic}")
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
                self.logger.debug(f"SIC {sic_code} maps to sector: {sector}")
                return sector
        
        self.logger.debug(f"No sector mapping found for SIC code: {sic_code}")
        return None
    
    def _fetch_sic_info(self, cik: str) -> dict | None:
        try:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            headers = {
                "User-Agent": "Company Name company@email.com",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            }
            self.logger.debug(f"Fetching submissions API: {url}")
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                self.logger.debug(f"Failed to get company metadata: HTTP {response.status_code}")
                return None
            
            data = response.json()
            self.logger.debug(f"Submissions API response keys: {list(data.keys())[:20]}")
            
            sic_info = {}
            if "sic" in data:
                sic_info["sic"] = data.get("sic")
                self.logger.debug(f"Found SIC in submissions API: {data.get('sic')}")
            if "sicDescription" in data:
                sic_info["sicDescription"] = data.get("sicDescription")
                self.logger.debug(f"Found sicDescription in submissions API: {data.get('sicDescription')}")
            if "industry" in data:
                sic_info["industry"] = data.get("industry")
                self.logger.debug(f"Found industry in submissions API: {data.get('industry')}")
            if "sector" in data:
                sic_info["sector"] = data.get("sector")
                self.logger.debug(f"Found sector in submissions API: {data.get('sector')}")
            
            return sic_info if sic_info else None
        except Exception as e:
            self.logger.debug(f"Failed to fetch SIC info: {e}")
            return None
