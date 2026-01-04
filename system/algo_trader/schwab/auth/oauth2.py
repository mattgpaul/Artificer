"""OAuth2 authentication handler for Schwab API.

This module provides functionality to handle OAuth2 authentication flow
for Schwab API, including authorization URL generation and token exchange.
"""

import base64
from typing import Any

import requests

from infrastructure.logging.logger import get_logger
from system.algo_trader.infra.redis.account import AccountBroker


class OAuth2Handler:
    """Handles OAuth2 authentication flow for Schwab API.

    Manages the OAuth2 authorization code flow, including generating authorization
    URLs, exchanging authorization codes for tokens, and storing tokens.

    Args:
        api_key: Schwab API key (client ID).
        secret: Schwab API secret (client secret).
        base_url: Base URL for Schwab API.
        account_broker: AccountBroker instance for token storage.
        logger: Optional logger instance. If not provided, creates a new logger.
    """

    def __init__(
        self, api_key: str, secret: str, base_url: str, account_broker: AccountBroker, logger=None
    ):
        """Initialize OAuth2Handler with API credentials.

        Args:
            api_key: Schwab API key (client ID).
            secret: Schwab API secret (client secret).
            base_url: Base URL for Schwab API.
            account_broker: AccountBroker instance for token storage.
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        self.api_key = api_key
        self.secret = secret
        self.base_url = base_url
        self.account_broker = account_broker
        self.logger = logger or get_logger(self.__class__.__name__)

    def authenticate(self) -> dict[str, Any] | None:
        """Perform OAuth2 authentication flow.

        Guides user through OAuth2 authorization flow, exchanging authorization
        code for access and refresh tokens, and storing them.

        Returns:
            Dictionary containing tokens if authentication succeeds, None otherwise.
        """
        self.logger.info("Starting OAuth2 authentication flow")

        auth_url = f"{self.base_url}/v1/oauth/authorize?client_id={self.api_key}&redirect_uri=https://127.0.0.1"
        print("\n" + "=" * 60)
        print("SCHWAB OAUTH2 AUTHENTICATION REQUIRED")
        print("=" * 60)
        print("Please visit this URL to authorize the application:")
        print(f"{auth_url}")
        print("\nAfter authorizing, you will be redirected to a URL.")
        print("Copy the ENTIRE redirect URL and paste it below.")
        print("=" * 60)

        returned_url = input("\nRedirect URL: ").strip()

        if not returned_url or "code=" not in returned_url:
            self.logger.error("Invalid redirect URL provided")
            return None

        try:
            code_start = returned_url.index("code=") + 5
            code_end = returned_url.index("%40")
            response_code = f"{returned_url[code_start:code_end]}@"

            tokens = self._exchange_code_for_tokens(response_code)

            if tokens:
                self.account_broker.set_access_token(tokens["access_token"])
                self.account_broker.set_refresh_token(tokens["refresh_token"])

                self._display_refresh_token_instructions(tokens["refresh_token"])

                self.logger.info("OAuth2 authentication completed successfully")
                return tokens

        except Exception as e:
            self.logger.error(f"OAuth2 flow failed: {e}")

        return None

    def _exchange_code_for_tokens(self, code: str) -> dict[str, Any] | None:
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

    def _display_refresh_token_instructions(self, refresh_token: str) -> None:
        print("\n" + "=" * 70)
        print("OAUTH2 FLOW COMPLETE - ACTION REQUIRED")
        print("=" * 70)
        print("\nYour new refresh token (valid for 90 days):")
        print(f"\n{refresh_token}\n")
        print("Please set this as an environment variable before next run:")
        print(f"\nexport SCHWAB_REFRESH_TOKEN={refresh_token}\n")
        print("Note: Token is stored in Redis for this session only.")
        print("Redis is ephemeral - you must set the env var for future runs.")
        print("=" * 70)

        input("\nPress ENTER to continue after copying the token...")
        self.logger.info("User confirmed token copied")
