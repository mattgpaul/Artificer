import requests
import base64
from datetime import datetime
from system.trader.schwab.timescale_enum import FrequencyType, PeriodType
from system.trader.redis.account import AccountBroker
from infrastructure.clients.schwab_client import SchwabClient
from infrastructure.logging.logger import get_logger

class MarketHandler(SchwabClient):
    def __init__(self):
        super().__init__()
        self.market_url = f"{self.base_url}/marketdata/v1"
        self.logger = get_logger(self.__class__.__name__)
        self.account = AccountBroker()

    def _load_token(self) -> str:
        token = self.account.get_access_token()
        if token is None:
            self.logger.info("Access token expired")
            self._refresh_token()
            token = self.account.get_access_token()
        
        return token

    def _refresh_token(self) -> dict:
        """Refresh expired access token using stored refresh token"""
        self.logger.info("Starting token refresh")
        
        # Load stored refresh token
        refresh_token = self.account.get_refresh_token()
        
        # Build request
        credentials = f"{self.api_key}:{self.secret}"
        headers = {
            "Authorization": f"Basic {base64.b64encode(credentials.encode()).decode()}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        
        self.logger.info("Sending token refresh request")
        response = requests.post(f"{self.base_url}/v1/oauth/token", headers=headers, data=payload)
        
        if response.status_code == 200:
            new_tokens = response.json()
            self.account.set_refresh_token(new_tokens["refresh_token"])
            self.account.set_access_token(new_tokens["access_token"])
            self.logger.info("Token refresh successful")
        else:
            self.logger.error(f"Token refresh failed: {response.status_code}")
            raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")

    def _construct_headers(self):
        token = self._load_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept" : "application/json",
        }
        return headers
        

    def _send_request(self, url: str, headers: dict, params: dict) -> dict:
        self.logger.info(f"Sending request to {url}")
        try:
            response = requests.get(url, headers=headers, params=params)
            self.logger.debug(f"Response status code: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error getting quotes: {e}")
            return None
        return response.json()

    def _extract_quote_data(self, response: dict) -> dict:
        self.logger.debug(f"Extracting quote data")
        extracted = {}
        
        for symbol, data in response.items():
            quote = data.get('quote', {})
            
            extracted[symbol] = {
                'price': quote.get('lastPrice'),
                'bid': quote.get('bidPrice'),
                'ask': quote.get('askPrice'),
                'volume': quote.get('totalVolume'),
                'change': quote.get('netChange'),
                'change_pct': quote.get('netPercentChange'),
                'timestamp': quote.get('tradeTime'),
            }
        
        return extracted

    def get_quotes(self, tickers: list[str]) -> dict:
        self.logger.info(f"Getting quotes for {tickers}")
        headers = self._construct_headers()
        url = self.market_url + "/quotes"
        params = {"symbols": tickers}
        response = self._send_request(url, headers, params)
        extracted_data = self._extract_quote_data(response)
        return extracted_data

    def get_price_history(
        self,
        ticker: str,
        period_type: PeriodType = PeriodType.YEAR,
        period: int = 1,
        frequency_type: FrequencyType = FrequencyType.DAILY,
        frequency: int = 1,
        extended_hours: bool = False,
    ) -> dict:
        self.logger.info(f"Getting price history for {ticker}")
        period_type.validate_combination(period, frequency_type, frequency)
        headers = self._construct_headers()
        url = self.market_url + "/pricehistory"
        params = {
            "symbol": ticker,
            "periodType": period_type.value,
            "period": period,
            "frequencyType": frequency_type.value,
            "frequency": frequency,
            "needExtendedHoursData": extended_hours,
        }
        response = self._send_request(url, headers, params)
        return response


    def get_option_chains(self, ticker: str) -> dict:
        pass

    def get_market_hours(self, date: datetime, markets: list[str] = ["equity"]) -> dict:
        self.logger.info(f"Getting {markets} hours for: {date}")
        headers = self._construct_headers()
        url = self.market_url + "/markets"
        params = {
            "markets": markets,
            "date": date.strftime("%Y-%m-%d")
        }
        response = self._send_request(url, headers, params)
        self.logger.debug(f"Response: {response}")
        
        if "EQ" in response["equity"].keys():
            equity_info = response["equity"]["EQ"]
        else:
            equity_info = response["equity"]["equity"]
        market_hours = {}
        market_hours["date"] = date.strftime("%Y-%m-%d")
        if equity_info["isOpen"]:
            #TODO: This needs to be able to handle after hours sessions
            self.logger.debug("Equity markets are open")
            regular_session = equity_info["sessionHours"]["regularMarket"][0]
            market_hours["start"] = regular_session["start"]
            market_hours["end"] = regular_session["end"]
        else:
            # market is closed, and the schwab API doesnt give you this info
            # Set start time to 9:30am Eastern for the given date (assume US/Eastern timezone)
            #TODO: account for daylight savings
            market_hours["start"] = date.replace(hour=9, minute=30, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S-04:00")
            market_hours["end"] = date.replace(hour=16, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S-04:00")
        return market_hours


