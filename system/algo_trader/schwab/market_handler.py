"""Schwab market data API handler.

This module provides the MarketHandler class for interacting with Schwab's
market data endpoints, including price history, quotes, and market hours
information.
"""

from datetime import datetime
from typing import Any

from infrastructure.logging.logger import get_logger
from system.algo_trader.schwab.schwab_client import SchwabClient
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


class MarketHandler(SchwabClient):
    """Schwab Market Data API Handler.

    Provides methods for retrieving market data including quotes, price history,
    and market hours. Inherits from SchwabClient for authentication and token management.
    """

    def __init__(self):
        """Initialize MarketHandler with market data API endpoint."""
        super().__init__()
        self.market_url = f"{self.base_url}/marketdata/v1"
        self.logger = get_logger(self.__class__.__name__)
        self.logger.info("MarketHandler initialized successfully")

    def _send_request(
        self, url: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Send authenticated request to Schwab API.

        Args:
            url: Full URL for the request
            params: Query parameters for the request

        Returns:
            Dict containing response data if successful, None otherwise
        """
        self.logger.debug(f"Sending request to {url}")
        try:
            response = self.make_authenticated_request("GET", url, params=params)
            self.logger.debug(f"Response status code: {response.status_code}")

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(
                    f"Request failed with status {response.status_code}: {response.text}"
                )
                return None
        except Exception as e:
            self.logger.error(f"Error making request: {e}")
            return None

    def _extract_quote_data(self, response: dict[str, Any]) -> dict[str, Any]:
        """Extract relevant quote data from Schwab API response.

        Args:
            response: Raw response from Schwab quotes API

        Returns:
            Dict containing extracted quote data for each symbol
        """
        self.logger.debug("Extracting quote data from response")
        extracted = {}

        for symbol, data in response.items():
            quote = data.get("quote", {})

            extracted[symbol] = {
                "price": quote.get("lastPrice"),
                "bid": quote.get("bidPrice"),
                "ask": quote.get("askPrice"),
                "volume": quote.get("totalVolume"),
                "change": quote.get("netChange"),
                "change_pct": quote.get("netPercentChange"),
                "timestamp": quote.get("tradeTime"),
            }

        return extracted

    def get_quotes(self, tickers: list[str]) -> dict[str, Any]:
        """Get real-time quotes for specified tickers.

        Args:
            tickers: List of stock symbols to get quotes for

        Returns:
            Dict containing quote data for each ticker
        """
        self.logger.info(f"Getting quotes for {tickers}")
        url = f"{self.market_url}/quotes"
        params = {"symbols": ",".join(tickers)}

        response = self._send_request(url, params)
        if response:
            return self._extract_quote_data(response)
        else:
            self.logger.error("Failed to get quotes")
            return {}

    def get_price_history(
        self,
        ticker: str,
        period_type: PeriodType = PeriodType.YEAR,
        period: int = 1,
        frequency_type: FrequencyType = FrequencyType.DAILY,
        frequency: int = 1,
        extended_hours: bool = False,
    ) -> dict[str, Any]:
        """Get historical price data for a ticker.

        Args:
            ticker: Stock symbol to get history for
            period_type: Type of period (day, month, year, ytd)
            period: Number of periods
            frequency_type: Frequency of data points (minute, daily, weekly, monthly)
            frequency: Frequency value (1, 5, 10, 15, 30 for minutes)
            extended_hours: Whether to include extended hours data

        Returns:
            Dict containing historical price data
        """
        self.logger.info(f"Getting price history for {ticker}")
        period_type.validate_combination(period, frequency_type, frequency)

        url = f"{self.market_url}/pricehistory"
        params = {
            "symbol": ticker,
            "periodType": period_type.value,
            "period": period,
            "frequencyType": frequency_type.value,
            "frequency": frequency,
            "needExtendedHoursData": extended_hours,
        }

        response = self._send_request(url, params)
        if response:
            return response
        else:
            self.logger.error(f"Failed to get price history for {ticker}")
            return {}

    def get_option_chains(self, ticker: str) -> dict[str, Any]:
        """Get option chain data for a ticker.

        Args:
            ticker: Stock symbol to get option chain for

        Returns:
            Dict containing option chain data
        """
        # TODO: Implement option chain functionality
        self.logger.warning(f"Option chain functionality not yet implemented for {ticker}")
        return {}

    def get_market_hours(self, date: datetime, markets: list[str] | None = None) -> dict[str, Any]:
        """Get market hours for specified date and markets.

        Args:
            date: Date to get market hours for
            markets: List of market types (e.g., ["equity"])

        Returns:
            Dict containing market hours information
        """
        if markets is None:
            markets = ["equity"]
        self.logger.info(f"Getting {markets} hours for: {date}")

        url = f"{self.market_url}/markets"
        params = {"markets": ",".join(markets), "date": date.strftime("%Y-%m-%d")}

        response = self._send_request(url, params)
        if not response:
            self.logger.error("Failed to get market hours")
            return {}

        self.logger.debug(f"Market hours response: {response}")

        # Extract equity market hours
        if "equity" in response:
            equity_data = response["equity"]
            if "EQ" in equity_data:
                equity_info = equity_data["EQ"]
            else:
                equity_info = equity_data.get("equity", {})

            market_hours = {"date": date.strftime("%Y-%m-%d")}

            if equity_info.get("isOpen", False):
                self.logger.debug("Equity markets are open")
                regular_session = equity_info["sessionHours"]["regularMarket"][0]
                market_hours["start"] = regular_session["start"]
                market_hours["end"] = regular_session["end"]
            else:
                self.logger.debug("Equity markets are closed")

            return market_hours
        else:
            self.logger.warning("No equity market data in response")
            return {"date": date.strftime("%Y-%m-%d")}
