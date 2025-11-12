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

    def _extract_all_periods_for_fact(
        self, facts: dict, fact_name: str, years_back: int = 10, require_quarterly: bool = True
    ) -> list[dict]:
        """Extract all periods for a given fact from company facts data.

        Args:
            facts: Company facts dictionary from SEC API.
            fact_name: Name of the fact to extract.
            years_back: Number of years back to include data.
            require_quarterly: Whether to require quarterly periods only.

        Returns:
            List of dictionaries containing period data with value, period_end, datetime, and unit.
        """
        periods = []
        facts_data = facts.get("facts", {})
        config = self.METRICS_CONFIG.get(fact_name, {})
        namespace = config.get("namespace", "us-gaap")
        unit_preference = config.get("unit_preference", [])

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

    def _build_time_series_dataframe(
        self, facts: dict, ticker: str, years_back: int = 10
    ) -> pd.DataFrame:
        all_data = {}
        shares_outstanding_data = {}

        for fact_name, config in self.METRICS_CONFIG.items():
            column_name = config["column"]
            require_quarterly = fact_name != "EntityCommonStockSharesOutstanding"
            periods = self._extract_all_periods_for_fact(
                facts, fact_name, years_back, require_quarterly
            )

            if fact_name == "EntityCommonStockSharesOutstanding":
                for period in periods:
                    datetime_ms = period["datetime"]
                    shares_outstanding_data[datetime_ms] = period["value"]
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

        return df

    def _extract_static_info(self, facts: dict, ticker: str) -> dict[str, str | None]:
        entity_name = facts.get("entityName")
        if isinstance(entity_name, dict):
            entity_name = entity_name.get("name", entity_name)
        elif not isinstance(entity_name, str):
            entity_name = None

        sic = facts.get("sic")
        sic_description = facts.get("sicDescription")

        return {
            "ticker": ticker,
            "sector": None,
            "industry": sic_description,
            "entity_name": entity_name,
            "sic": str(sic) if sic else None,
        }

    def get_company_facts(self, ticker: str) -> dict | None:
        """Retrieve company facts data for a given ticker.

        Fetches company facts from SEC API and processes them into static
        information and time series DataFrame.

        Args:
            ticker: Stock ticker symbol to retrieve facts for.

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
        time_series_df = self._build_time_series_dataframe(facts, ticker.upper())

        return {"static": static_info, "time_series": time_series_df}
