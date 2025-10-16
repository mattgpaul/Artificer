import os
import requests
import base64
from typing import Optional, Dict, Any
from infrastructure.client import Client
from infrastructure.logging.logger import get_logger


class SchwabClient(Client):
    """
    Base client for Schwab API interactions.
    
    Handles OAuth2 authentication flow and API requests.
    Does NOT manage token storage - that's the responsibility of the calling code.
    """
    
    def __init__(self, api_key: Optional[str] = None, secret: Optional[str] = None):
        """
        Initialize Schwab API client.
        
        Arguments:
            api_key: Schwab API key (if None, will attempt to load from SCHWAB_API_KEY env var)
            secret: Schwab API secret (if None, will attempt to load from SCHWAB_SECRET env var)
        """
        super().__init__()
        self.api_key = api_key or os.getenv("SCHWAB_API_KEY")
        self.secret = secret or os.getenv("SCHWAB_SECRET")
        self.base_url = "https://api.schwabapi.com"
        self.logger = get_logger(self.__class__.__name__)
        
        if not self.api_key or not self.secret:
            raise ValueError("SCHWAB_API_KEY and SCHWAB_SECRET must be provided or set in environment")

    def get_authorization_url(self, redirect_uri: str = "https://127.0.0.1") -> str:
        """
        Get the OAuth2 authorization URL for user to visit.
        
        Arguments:
            redirect_uri: OAuth redirect URI (must match app configuration)
            
        Returns:
            Authorization URL string
        """
        auth_url = f"{self.base_url}/v1/oauth/authorize?client_id={self.api_key}&redirect_uri={redirect_uri}"
        self.logger.debug(f"Generated authorization URL")
        return auth_url
    
    def get_tokens_from_code(self, auth_code: str, redirect_uri: str = "https://127.0.0.1") -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Arguments:
            auth_code: Authorization code from OAuth callback
            redirect_uri: OAuth redirect URI (must match the one used for authorization)
            
        Returns:
            Dictionary containing access_token, refresh_token, expires_in, etc.
            
        Raises:
            Exception: If token exchange fails
        """
        credentials = f"{self.api_key}:{self.secret}"
        base64_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        
        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        payload = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": redirect_uri,
        }
        
        self.logger.debug("Exchanging authorization code for tokens")
        response = requests.post(f"{self.base_url}/v1/oauth/token", headers=headers, data=payload)
        
        if response.status_code == 200:
            self.logger.info("Successfully obtained tokens from authorization code")
            return response.json()
        else:
            self.logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using a refresh token.
        
        Arguments:
            refresh_token: Valid refresh token
            
        Returns:
            Dictionary containing new access_token, expires_in, etc.
            Note: refresh_token is NOT included in response (Schwab keeps the same one)
            
        Raises:
            Exception: If token refresh fails
        """
        credentials = f"{self.api_key}:{self.secret}"
        headers = {
            "Authorization": f"Basic {base64.b64encode(credentials.encode()).decode()}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        self.logger.debug("Refreshing access token")
        response = requests.post(f"{self.base_url}/v1/oauth/token", headers=headers, data=payload)
        
        if response.status_code == 200:
            self.logger.info("Token refresh successful")
            return response.json()
        else:
            self.logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
            raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")

