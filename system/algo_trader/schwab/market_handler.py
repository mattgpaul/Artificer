import requests
import base64
from datetime import datetime
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType
from system.algo_trader.redis.account import AccountBroker
from infrastructure.schwab.schwab import SchwabClient
from infrastructure.logging.logger import get_logger

class MarketHandler(SchwabClient):
    def __init__(self):
        super().__init__()
        self.market_url = f"{self.base_url}/marketdata/v1"
        self.logger = get_logger(self.__class__.__name__)
        self.account = AccountBroker()
        # Local tokens file in algo_trader directory
        self.local_tokens_file = '/home/matthew/Artificer/system/algo_trader/schwab/tokens.json'

    def _load_token(self) -> str:
        """Get valid access token, refreshing if necessary"""
        # First try to get from Redis
        token = self.account.get_access_token()
        if token is None:
            self.logger.info("Access token not found in Redis, attempting refresh")
            self._refresh_token()
            token = self.account.get_access_token()
        
        if token is None:
            self.logger.info("No tokens in Redis, checking local tokens file")
            self._load_tokens_from_file()
            token = self.account.get_access_token()
        
        if token is None:
            self.logger.info("No tokens available, starting OAuth2 flow")
            self._perform_oauth2_flow()
            token = self.account.get_access_token()
        
        return token

    def _load_tokens_from_file(self) -> bool:
        """Load tokens from local file and push to Redis"""
        try:
            import json
            from datetime import datetime
            
            with open(self.local_tokens_file, 'r') as f:
                tokens = json.load(f)
            
            # Check if tokens are expired
            expires_at = datetime.fromisoformat(tokens['expires_at'])
            if datetime.now() >= expires_at:
                self.logger.info("Local tokens are expired, will need refresh")
                # Still load refresh token for potential refresh
                if 'refresh_token' in tokens:
                    self.account.set_refresh_token(tokens['refresh_token'])
                return False
            
            # Tokens are valid, save to Redis
            self.account.set_access_token(tokens['access_token'])
            self.account.set_refresh_token(tokens['refresh_token'])
            
            self.logger.info("Tokens loaded from local file and saved to Redis")
            return True
            
        except FileNotFoundError:
            self.logger.info("No local tokens file found")
            return False
        except Exception as e:
            self.logger.error(f"Error loading tokens from file: {e}")
            return False

    def _refresh_token(self) -> dict:
        """Refresh expired access token using stored refresh token"""
        self.logger.info("Starting token refresh")
        
        # Load stored refresh token from Redis
        refresh_token = self.account.get_refresh_token()
        if refresh_token is None:
            self.logger.warning("No refresh token found in Redis")
            return None
        
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
            # Keep the original refresh token if not provided in response
            if "refresh_token" not in new_tokens:
                new_tokens["refresh_token"] = refresh_token
            
            # Save tokens to Redis
            self.account.set_refresh_token(new_tokens["refresh_token"])
            self.account.set_access_token(new_tokens["access_token"])
            self.logger.info("Token refresh successful")
            return new_tokens
        else:
            self.logger.error(f"Token refresh failed: {response.status_code}")
            raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")

    def _perform_oauth2_flow(self) -> dict:
        """Perform complete OAuth2 flow and save tokens to Redis"""
        self.logger.info("Starting OAuth2 authentication flow")
        
        # Step 1: Show auth URL
        auth_url = f"{self.base_url}/v1/oauth/authorize?client_id={self.api_key}&redirect_uri=https://127.0.0.1"
        self.logger.info("Click to authenticate:")
        self.logger.info(auth_url)
        
        # Step 2: Get redirect URL from user  
        print("After authorizing, paste the redirect URL here:")
        returned_url = input("Redirect URL: ")
        
        # Step 3: Extract code (Schwab-specific format)
        response_code = f"{returned_url[returned_url.index('code=') + 5: returned_url.index('%40')]}@"
        
        # Step 4: Build request and get tokens
        credentials = f"{self.api_key}:{self.secret}"
        base64_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        
        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        payload = {
            "grant_type": "authorization_code",
            "code": response_code, 
            "redirect_uri": "https://127.0.0.1",
        }
        
        response = requests.post(f"{self.base_url}/v1/oauth/token", headers=headers, data=payload)
        
        if response.status_code == 200:
            tokens = response.json()
            self.logger.info("OAuth2 authentication successful")
            
            # Save tokens to Redis
            self.account.set_refresh_token(tokens["refresh_token"])
            self.account.set_access_token(tokens["access_token"])
            
            # Also save to local workspace for backup
            self._save_tokens_to_workspace(tokens)
            
            return tokens
        else:
            self.logger.error(f"OAuth2 authentication failed: {response.status_code}")
            raise Exception(f"OAuth2 authentication failed: {response.status_code} - {response.text}")

    def _save_tokens_to_workspace(self, tokens: dict) -> None:
        """Save tokens to local algo_trader directory as backup"""
        import json
        from datetime import datetime, timedelta
        
        now = datetime.now()
        expires_in = tokens.get('expires_in', 1800)
        expires_at = now + timedelta(seconds=expires_in)
        
        token_data = {
            'access_token': tokens.get('access_token'),
            'refresh_token': tokens.get('refresh_token'),
            'token_type': tokens.get('token_type', 'Bearer'),
            'expires_in': expires_in,
            'expires_at': expires_at.isoformat(),
            'created_at': now.isoformat()
        }
        
        # Save to local algo_trader tokens file
        with open(self.local_tokens_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        self.logger.info(f"Tokens saved to local file: {self.local_tokens_file}")

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
        return market_hours


