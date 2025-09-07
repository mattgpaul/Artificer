import os
import json
import dotenv
import requests
import base64
from datetime import datetime, timedelta
from infrastructure.client import Client
from infrastructure.logging.logger import get_logger

class SchwabClient(Client): 
    def __init__(self):
        dotenv.load_dotenv(dotenv.find_dotenv("artificer.env"))
        self.api_key = os.getenv("SCHWAB_API_KEY")
        self.secret = os.getenv("SCHWAB_SECRET")
        self.app_name = os.getenv("SCHWAB_APP_NAME")
        self.base_url = "https://api.schwabapi.com"
        self.logger = get_logger(self.__class__.__name__)
        # Use absolute path to actual source directory
        workspace_root = "/home/matthew/Artificer"  # TODO: make this dynamic later
        #TODO: put this in the redis db
        self.token_file = os.path.join(workspace_root, "infrastructure/clients/schwab/schwab_tokens.json")

    def get_initial_tokens(self) -> dict:
        """One-time OAuth2 setup to get initial tokens"""
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
        return response.json()

    def _save_token(self, tokens: dict) -> None:
        """Save tokens to schwab directory"""
        #TODO: change this to default to this directory
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
        
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        self.logger.info(f"Tokens saved to {self.token_file}")

    def _load_token(self) -> str:
        """Get valid access token, refreshing if necessary"""
        try:
            self.logger.debug(f"token filepath {self.token_file}")
            with open(self.token_file, 'r') as f:
                tokens = json.load(f)
        except FileNotFoundError:
            raise Exception("No tokens found - run initial authentication first")
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(tokens['expires_at'])
        if datetime.now() >= expires_at:
            self.logger.info("Access token expired, refreshing...")
            tokens = self._refresh_token()
        
        return tokens['access_token']

    def _refresh_token(self) -> dict:
        """Refresh expired access token using stored refresh token"""
        self.logger.info("Starting token refresh")
        
        # Load stored refresh token
        try:
            with open(self.token_file, 'r') as f:
                refresh_token = json.load(f)['refresh_token']
        except (FileNotFoundError, KeyError):
            self.logger.error("No refresh token found")
            raise Exception("No refresh token found - run initial authentication first")
        
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
            new_tokens['refresh_token'] = refresh_token  # Keep original refresh token
            self._save_token(new_tokens) 
            self.logger.info("Token refresh successful")
            return new_tokens
        else:
            self.logger.error(f"Token refresh failed: {response.status_code}")
            raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    client = SchwabClient()
    response = client.get_initial_tokens()
    print(response)
    client._save_token(response)
