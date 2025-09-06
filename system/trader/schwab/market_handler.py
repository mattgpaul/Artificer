import requests
import base64
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
        period_type: PeriodType,
        period: int,
        frequency_type: FrequencyType,
        frequency: int,
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

    def get_market_hours(self, ticker: str) -> dict:
        pass

if __name__ == "__main__":
    handler = MarketHandler()
    try:
        quotes = handler.get_quotes(["AAPL", "MSFT"])
        print(quotes)
        historical = handler.get_price_history(
            ticker="NVDA",
            period_type=PeriodType.DAY,
            period=1,
            frequency_type=FrequencyType.MINUTE,
            frequency=1,
        )
        print(historical)
    except Exception as e:
        print(f"Error: {e}")
