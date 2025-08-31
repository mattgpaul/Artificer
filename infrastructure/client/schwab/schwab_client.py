import os
import json
import dotenv
import requests
import base64
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from infrastructure.client.client import Client
from infrastructure.logging.logger import get_logger

class SchwabClient(Client): 
    def __init__(self):
        dotenv.load_dotenv(dotenv.find_dotenv("artificer.env"))
        self.api_key = os.getenv("SCHWAB_API_KEY")
        self.secret = os.getenv("SCHWAB_SECRET")
        self.app_name = os.getenv("SCHWAB_APP_NAME")
        self.logger = get_logger(self.__class__.__name__)
        self.token_file = "infrastructure/client/schwab/schwab_tokens.json"

    def get_initial_tokens(self) -> dict:
        """One-time OAuth2 setup to get initial tokens"""
        # Step 1: Show auth URL
        auth_url = f"https://api.schwabapi.com/v1/oauth/authorize?client_id={self.api_key}&redirect_uri=https://127.0.0.1"
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
        
        response = requests.post("https://api.schwabapi.com/v1/oauth/token", headers=headers, data=payload)
        return response.json()

    def refresh_token(self) -> None:
        pass

    def save_token(self, tokens: dict) -> None:
        """Save tokens to schwab directory"""
        # Add expiration timestamp
        expires_in = tokens.get('expires_in', 1800)
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        token_data = {
            'access_token': tokens.get('access_token'),
            'refresh_token': tokens.get('refresh_token'),
            'token_type': tokens.get('token_type', 'Bearer'),
            'expires_in': expires_in,
            'expires_at': expires_at.isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        self.logger.info(f"Tokens saved to {self.token_file}")
        print(f"Tokens saved to {self.token_file}")

    def load_token(self) -> str:
        # include check if token is expired
        pass


if __name__ == "__main__":
    print("Testing Schwab OAuth2 authentication...")
    client = SchwabClient()
    try:
        pass
        
    except Exception as e:
        print(f"ERROR: {e}")
