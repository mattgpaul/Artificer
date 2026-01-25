"""OAuth2 authentication entry point for Schwab API.

This script provides a simple command-line interface to perform OAuth2
authentication for the Schwab API using the SchwabClient.
"""

from algo_trader.infra.schwab.schwab_client import SchwabClient


def main() -> None:
    """Perform OAuth2 authentication flow."""
    client = SchwabClient()
    client.authenticate()


if __name__ == "__main__":
    main()
