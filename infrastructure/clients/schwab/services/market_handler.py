import requests
from infrastructure.client.schwab.services.timescale_enum import FrequencyType, PeriodType
from infrastructure.client.schwab.schwab_client import SchwabClient
from infrastructure.logging.logger import get_logger

class MarketHandler(SchwabClient):
    def __init__(self):
        super().__init__()
        self.market_url = f"{self.base_url}/marketdata/v1"
        self.logger = get_logger(self.__class__.__name__)

    def _construct_headers(self):
        token = self.load_token()
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
        self.logger.info(f"Extracting quote data")
        extracted = {}
        
        for symbol, data in response.items():
            quote = data.get('quote', {})
            fundamental = data.get('fundamental', {})
            
            extracted[symbol] = {
                'price': quote.get('lastPrice'),
                'bid': quote.get('bidPrice'),
                'ask': quote.get('askPrice'),
                'volume': quote.get('totalVolume'),
                'change': quote.get('netChange'),
                'change_pct': quote.get('netPercentChange'),
                'pe_ratio': fundamental.get('peRatio'),
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
