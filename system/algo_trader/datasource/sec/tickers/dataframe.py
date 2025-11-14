"""DataFrame builder for SEC tickers data.

This module provides functionality to build time series DataFrames from
SEC company facts data.
"""

from datetime import datetime, timezone

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.datasource.sec.company_facts_config import load_company_facts_config


class TickersDataFrameBuilder:
    """Builder for time series DataFrames from SEC company facts.

    Converts SEC company facts JSON data into pandas DataFrames with
    proper time series formatting.
    """

    METRICS_CONFIG: dict[str, dict] = load_company_facts_config()

    def __init__(self, logger=None):
        """Initialize DataFrame builder.

        Args:
            logger: Optional logger instance. If not provided, creates a new one.
        """
        self.logger = logger or get_logger(self.__class__.__name__)

    def _validate_fact_exists(self, facts_data: dict, namespace: str, fact_name: str) -> bool:
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
        facts_data = facts.get("facts", {})
        config = self.METRICS_CONFIG.get(fact_name, {})
        namespace = config.get("namespace", "us-gaap")
        unit_preference = config.get("unit_preference", [])
        alternatives = config.get("alternatives", [])

        periods = self._extract_periods_for_single_fact(
            facts_data, namespace, fact_name, unit_preference, years_back, require_quarterly
        )

        if not periods and alternatives:
            self.logger.info(
                f"Fact {fact_name} has no valid periods in namespace {namespace}, "
                f"trying alternatives: {alternatives}"
            )
            self.logger.debug(
                f"Fact {fact_name} has no valid periods in namespace {namespace}, "
                f"trying alternatives: {alternatives}"
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
                    f"Fact {fact_name} and all alternatives {alternatives} "
                    f"yielded no valid periods in namespace {namespace}"
                )

        return periods

    def build_time_series_dataframe(
        self, facts: dict, ticker: str, years_back: int = 10
    ) -> pd.DataFrame:
        """Build time series DataFrame from company facts data.

        Args:
            facts: Company facts dictionary from SEC API.
            ticker: Ticker symbol.
            years_back: Number of years to look back for data. Default: 10.

        Returns:
            DataFrame with time series data indexed by datetime.
        """
        all_data = {}
        shares_outstanding_data = {}
        market_cap_data = {}

        for fact_name, config in self.METRICS_CONFIG.items():
            column_name = config["column"]
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

            df["market_cap"] = pd.NA

            for idx in df.index:
                market_cap_on_or_before = market_cap_df[market_cap_df.index <= idx]
                if not market_cap_on_or_before.empty:
                    df.loc[idx, "market_cap"] = float(
                        market_cap_on_or_before["market_cap"].iloc[-1]
                    )

            df["market_cap"] = pd.to_numeric(df["market_cap"], errors="coerce")
            df["market_cap"] = df["market_cap"].ffill()
        else:
            df["market_cap"] = pd.NA

        return df
