import os
import json
import requests
from typing import Optional, Dict, Any
from infrastructure.clients.schwab_client import SchwabClient
from infrastructure.logging.logger import get_logger
from system.algo_trader.clients.redis_client import AlgoTraderRedisClient


class AlgoTraderSchwabClient:
    """
    System-level client for Schwab API interactions.
    
    Manages authentication, token refresh, and market data retrieval
    for the algo_trader system. Uses Redis for token storage.
    """
    
    def __init__(self, redis_client: AlgoTraderRedisClient, token_file_path: str = "/home/matthew/Artificer/system/algo_trader/.tokens.json"):
        """
        Initialize Schwab client.
        
        Arguments:
            redis_client: Redis client instance for access token storage (short-lived)
            token_file_path: Path to persistent token file for refresh token storage
        """
        self.logger = get_logger(self.__class__.__name__)
        self.redis = redis_client
        self.schwab_client = SchwabClient()  # Will load credentials from env
        self.base_url = self.schwab_client.base_url
        self.redirect_uri = "https://127.0.0.1"
        self.token_file_path = token_file_path
        self._auth_attempted_this_session = False  # Track if we've already tried to authenticate this session
    
    def _read_refresh_token_from_file(self) -> Optional[str]:
        """
        Read refresh token from persistent token file.
        
        Returns:
            Refresh token string if found, None otherwise
        """
        try:
            if not os.path.exists(self.token_file_path):
                self.logger.debug("Token file does not exist")
                return None
            
            with open(self.token_file_path, 'r') as f:
                tokens = json.load(f)
                refresh_token = tokens.get('refresh_token')
                
                if refresh_token:
                    self.logger.debug("Read refresh token from token file")
                    return refresh_token
                else:
                    self.logger.debug("No refresh token found in token file")
                    return None
        except Exception as e:
            self.logger.error(f"Error reading token file: {e}")
            return None
    
    def _write_refresh_token_to_file(self, refresh_token: str) -> bool:
        """
        Write refresh token to persistent token file.
        
        Arguments:
            refresh_token: Refresh token to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.token_file_path), exist_ok=True)
            
            # Read existing tokens if file exists
            tokens = {}
            if os.path.exists(self.token_file_path):
                try:
                    with open(self.token_file_path, 'r') as f:
                        tokens = json.load(f)
                except json.JSONDecodeError:
                    self.logger.warning("Token file corrupted, creating new one")
            
            # Update refresh token
            tokens['refresh_token'] = refresh_token
            
            # Write back to file with restrictive permissions
            with open(self.token_file_path, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            # Set file permissions to 600 (owner read/write only)
            os.chmod(self.token_file_path, 0o600)
            
            self.logger.info("Refresh token written to token file")
            return True
        except Exception as e:
            self.logger.error(f"Error writing token file: {e}")
            return False
        
    def authenticate(self) -> bool:
        """
        Perform initial OAuth2 authentication and store tokens.
        
        Interactive flow that prompts user to visit authorization URL
        and paste back the redirect URL.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            self.logger.info("Starting initial authentication flow")
            
            # Step 1: Get and display authorization URL
            auth_url = self.schwab_client.get_authorization_url(self.redirect_uri)
            self.logger.info("Visit this URL to authorize:")
            print(f"\n{auth_url}\n")
            
            # Step 2: Get redirect URL from user
            print("After authorizing, paste the full redirect URL here:")
            returned_url = input("Redirect URL: ")
            
            # Step 3: Extract authorization code (Schwab-specific format)
            # Schwab returns code in format: ...?code=XXXXX%40&...
            # We need to extract and decode it
            auth_code = f"{returned_url[returned_url.index('code=') + 5: returned_url.index('%40')]}@"
            
            # Step 4: Exchange code for tokens
            tokens = self.schwab_client.get_tokens_from_code(auth_code, self.redirect_uri)
            
            if 'access_token' in tokens and 'refresh_token' in tokens:
                # Store access token in Redis (short-lived, 30 min TTL)
                expires_in = tokens.get('expires_in', 1800)
                self.redis.store_access_token(tokens['access_token'], ttl=expires_in)
                
                # Store refresh token in persistent token file (survives reboots)
                self._write_refresh_token_to_file(tokens['refresh_token'])
                
                self.logger.info("Authentication successful, tokens stored")
                return True
            else:
                self.logger.error(f"Authentication failed: {tokens}")
                return False
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    def _get_valid_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.
        
        Automatically triggers OAuth2 authentication if refresh token is invalid.
        Only attempts authentication once per session to avoid multiple prompts.
        
        Returns:
            Valid access token string, None if unable to get token
        """
        # Try to get existing access token from Redis
        token = self.redis.get_access_token()
        
        if token:
            self.logger.debug("Using existing access token from Redis")
            return token
        
        # Token expired or doesn't exist, try to refresh
        self.logger.info("Access token expired or missing, attempting refresh")
        refresh_token = self._read_refresh_token_from_file()
        
        if not refresh_token:
            # Only attempt OAuth2 once per session
            if not self._auth_attempted_this_session:
                self.logger.warning("No refresh token found in token file, triggering OAuth2 authentication")
                self._auth_attempted_this_session = True
                if self.authenticate():
                    return self.redis.get_access_token()
                else:
                    self.logger.error("OAuth2 authentication failed")
                    return None
            else:
                self.logger.error("No refresh token available and authentication already attempted this session")
                return None
        
        # Perform token refresh
        new_token = self._refresh_token(refresh_token)
        
        # If refresh failed, trigger OAuth2 re-authentication (once per session)
        if not new_token:
            if not self._auth_attempted_this_session:
                self.logger.warning("Token refresh failed, triggering OAuth2 re-authentication")
                self._auth_attempted_this_session = True
                if self.authenticate():
                    return self.redis.get_access_token()
                else:
                    self.logger.error("OAuth2 re-authentication failed")
                    return None
            else:
                self.logger.error("Token refresh failed and authentication already attempted this session")
                return None
        
        return new_token
    
    def _refresh_token(self, refresh_token: str) -> Optional[str]:
        """
        Refresh access token using refresh token.
        
        Arguments:
            refresh_token: Current refresh token
            
        Returns:
            New access token if successful, None otherwise
        """
        try:
            self.logger.debug("Attempting to refresh access token")
            tokens = self.schwab_client.refresh_access_token(refresh_token)
            
            expires_in = tokens.get('expires_in', 1800)
            access_token = tokens['access_token']
            
            # Store new access token in Redis
            self.redis.store_access_token(access_token, ttl=expires_in)
            self.logger.info("Token refresh successful")
            return access_token
        except Exception as e:
            self.logger.error(f"Error refreshing token: {e}")
            return None
    
    def get_price_history(
        self,
        symbol: str,
        period_type: str = "month",
        period: int = 1,
        frequency_type: str = "daily",
        frequency: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Get historical price data for a symbol.
        
        Arguments:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            period_type: Period type - 'day', 'month', 'year', 'ytd'
            period: Number of periods (depends on period_type)
            frequency_type: Frequency type - 'minute', 'daily', 'weekly', 'monthly'
            frequency: Frequency interval (1, 5, 10, 15, 30 for minute)
            
        Returns:
            Dictionary containing price history data, None if request fails
        """
        token = self._get_valid_token()
        
        if not token:
            self.logger.error("Unable to get valid access token for price history")
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            
            params = {
                "periodType": period_type,
                "period": period,
                "frequencyType": frequency_type,
                "frequency": frequency
            }
            
            url = f"{self.base_url}/marketdata/v1/pricehistory"
            self.logger.debug(f"Fetching price history for {symbol}")
            
            response = requests.get(
                url,
                headers=headers,
                params={**params, "symbol": symbol}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Successfully retrieved price history for {symbol}")
                return data
            else:
                self.logger.error(f"Price history request failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching price history: {e}")
            return None

