"""
Schwab API Client - Consolidated OAuth2 and Token Management

This module provides the core Schwab API client with Redis-first token management,
proper OAuth2 flow, and automatic token refresh capabilities.

Token Flow:
1. Check Redis for valid access token (TTL: 30 min)
2. If expired, check Redis for refresh token (TTL: 90 days) → refresh access token
3. If refresh token missing from Redis, load from env and store in Redis → refresh access token
4. If refresh token expired, initiate OAuth2 flow → save to Redis AND update env file
"""

import os
import json
import requests
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from abc import ABC, abstractmethod

from infrastructure.client import Client
from infrastructure.logging.logger import get_logger
from system.algo_trader.redis.account import AccountBroker


class SchwabClient(Client):
    """
    Consolidated Schwab API client with Redis-first token management.
    
    This client handles OAuth2 authentication, token refresh, and provides
    a base for Schwab API operations. Tokens are stored in Redis with proper
    TTL management, with environment file fallback for bootstrap scenarios.
    """
    
    def __init__(self):
        """Initialize Schwab client with environment configuration."""
        self.logger = get_logger(self.__class__.__name__)
        
        # Load configuration from environment variables
        self.api_key = os.getenv("SCHWAB_API_KEY")
        self.secret = os.getenv("SCHWAB_SECRET") 
        self.app_name = os.getenv("SCHWAB_APP_NAME")
        self.base_url = "https://api.schwabapi.com"
        
        # Validate required environment variables
        if not all([self.api_key, self.secret, self.app_name]):
            raise ValueError(
                "Missing required Schwab environment variables. "
                "Please set SCHWAB_API_KEY, SCHWAB_SECRET, and SCHWAB_APP_NAME"
            )
        
        # Initialize Redis broker for token management
        self.account_broker = AccountBroker()
        
        # Environment file path for token persistence (bootstrap only)
        self.env_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "algo_trader.env"
        )
        
        self.logger.info("SchwabClient initialized successfully")

    def get_valid_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        This method implements the complete token lifecycle:
        1. Check Redis for valid access token
        2. If expired/missing, attempt refresh using Redis refresh token
        3. If refresh token missing, load from env file and store in Redis
        4. If refresh token expired, initiate OAuth2 flow
        
        Returns:
            str: Valid access token
            
        Raises:
            Exception: If unable to obtain valid token after all attempts
        """
        self.logger.debug("Attempting to get valid access token")
        
        # Step 1: Check Redis for valid access token
        access_token = self.account_broker.get_access_token()
        if access_token:
            self.logger.debug("Found valid access token in Redis")
            return access_token
        
        self.logger.info("No valid access token in Redis, attempting refresh")
        
        # Step 2: Try to refresh using Redis refresh token
        if self.refresh_token():
            access_token = self.account_broker.get_access_token()
            if access_token:
                self.logger.info("Successfully refreshed access token from Redis")
                return access_token
        
        self.logger.info("Redis refresh failed, checking environment file")
        
        # Step 3: Load refresh token from env file and store in Redis
        if self.load_token():
            if self.refresh_token():
                access_token = self.account_broker.get_access_token()
                if access_token:
                    self.logger.info("Successfully refreshed access token from env file")
                    return access_token
        
        self.logger.warning("All refresh attempts failed, initiating OAuth2 flow")
        
        # Step 4: Perform complete OAuth2 flow
        tokens = self.authenticate()
        if tokens and tokens.get('access_token'):
            self.logger.info("OAuth2 flow completed successfully")
            return tokens['access_token']
        
        raise Exception("Unable to obtain valid access token after all attempts")

    def refresh_token(self) -> bool:
        """
        Refresh access token using stored refresh token.
        
        Returns:
            bool: True if refresh was successful, False otherwise
        """
        refresh_token = self.account_broker.get_refresh_token()
        if not refresh_token:
            self.logger.debug("No refresh token found in Redis")
            return False
        
        try:
            # Make refresh request
            credentials = f"{self.api_key}:{self.secret}"
            headers = {
                "Authorization": f"Basic {base64.b64encode(credentials.encode()).decode()}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}
            
            self.logger.debug("Sending token refresh request to Schwab API")
            response = requests.post(f"{self.base_url}/v1/oauth/token", headers=headers, data=payload)
            
            if response.status_code == 200:
                tokens = response.json()
                # Keep the original refresh token if not provided in response
                if "refresh_token" not in tokens:
                    tokens["refresh_token"] = refresh_token
                
                # Store new tokens in Redis
                self.account_broker.set_access_token(tokens['access_token'])
                if tokens.get('refresh_token'):
                    self.account_broker.set_refresh_token(tokens['refresh_token'])
                
                # Update env file with new tokens for persistence
                self._update_env_file_with_tokens(tokens)
                
                self.logger.info("Successfully refreshed access token")
                return True
            else:
                self.logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to refresh token: {e}")
        
        return False

    def load_token(self) -> bool:
        """
        Load refresh token from environment and store in Redis.
        
        Returns:
            bool: True if refresh token was loaded and stored, False otherwise
        """
        try:
            refresh_token = os.getenv("SCHWAB_REFRESH_TOKEN")
            if refresh_token:
                self.account_broker.set_refresh_token(refresh_token)
                self.logger.info("Loaded refresh token from environment and stored in Redis")
                return True
        except Exception as e:
            self.logger.error(f"Failed to load refresh token from env: {e}")
        
        return False

    def authenticate(self) -> Optional[Dict[str, Any]]:
        """
        Perform complete OAuth2 authentication flow.
        
        Returns:
            Dict containing tokens if successful, None otherwise
        """
        self.logger.info("Starting OAuth2 authentication flow")
        
        # Step 1: Show auth URL
        auth_url = f"{self.base_url}/v1/oauth/authorize?client_id={self.api_key}&redirect_uri=https://127.0.0.1"
        print("\n" + "="*60)
        print("SCHWAB OAUTH2 AUTHENTICATION REQUIRED")
        print("="*60)
        print(f"Please visit this URL to authorize the application:")
        print(f"{auth_url}")
        print("\nAfter authorizing, you will be redirected to a URL.")
        print("Copy the ENTIRE redirect URL and paste it below.")
        print("="*60)
        
        # Step 2: Get redirect URL from user  
        returned_url = input("\nRedirect URL: ").strip()
        
        if not returned_url or 'code=' not in returned_url:
            self.logger.error("Invalid redirect URL provided")
            return None
        
        try:
            # Step 3: Extract code (Schwab-specific format)
            code_start = returned_url.index('code=') + 5
            code_end = returned_url.index('%40')
            response_code = f"{returned_url[code_start:code_end]}@"
            
            # Step 4: Exchange code for tokens
            tokens = self._exchange_code_for_tokens(response_code)
            
            if tokens:
                # Store tokens in Redis
                self.account_broker.set_access_token(tokens['access_token'])
                self.account_broker.set_refresh_token(tokens['refresh_token'])
                
                # Update env file with new tokens
                self._update_env_file_with_tokens(tokens)
                
                self.logger.info("OAuth2 authentication completed successfully")
                return tokens
                
        except Exception as e:
            self.logger.error(f"OAuth2 flow failed: {e}")
        
        return None

    def _exchange_code_for_tokens(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from OAuth2 flow
            
        Returns:
            Dict containing tokens if successful, None otherwise
        """
        credentials = f"{self.api_key}:{self.secret}"
        base64_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        
        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        payload = {
            "grant_type": "authorization_code",
            "code": code, 
            "redirect_uri": "https://127.0.0.1",
        }
        
        self.logger.debug("Exchanging authorization code for tokens")
        response = requests.post(f"{self.base_url}/v1/oauth/token", headers=headers, data=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            return None

    def _update_env_file_with_tokens(self, tokens: Dict[str, Any]) -> None:
        """
        Update environment file with new tokens for persistence.
        
        Args:
            tokens: Dictionary containing access_token and refresh_token
        """
        try:
            # Read current env file
            env_lines = []
            if os.path.exists(self.env_file_path):
                with open(self.env_file_path, 'r') as f:
                    env_lines = f.readlines()
            
            # Update or add token lines
            token_lines = {
                'SCHWAB_ACCESS_TOKEN': tokens.get('access_token', ''),
                'SCHWAB_REFRESH_TOKEN': tokens.get('refresh_token', '')
            }
            
            # Remove existing token lines and add new ones
            env_lines = [line for line in env_lines 
                        if not line.startswith('SCHWAB_ACCESS_TOKEN=') 
                        and not line.startswith('SCHWAB_REFRESH_TOKEN=')]
            
            for key, value in token_lines.items():
                if value:  # Only add if token exists
                    env_lines.append(f"export {key}={value}\n")
            
            # Write updated env file
            with open(self.env_file_path, 'w') as f:
                f.writelines(env_lines)
            
            self.logger.info(f"Updated environment file with new tokens: {self.env_file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to update environment file: {e}")

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.
        
        Returns:
            Dict containing Authorization header with valid access token
        """
        token = self.get_valid_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    def make_authenticated_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make an authenticated HTTP request to the Schwab API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL for the request
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            requests.Response object
        """
        headers = self.get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        
        kwargs['headers'] = headers
        
        self.logger.debug(f"Making {method} request to {url}")
        return requests.request(method, url, **kwargs)
