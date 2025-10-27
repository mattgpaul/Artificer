"""SEC ticker data retrieval module."""

import requests

from infrastructure.logging.logger import get_logger


class Tickers:
    """Class for retrieving ticker data from SEC.gov."""

    def __init__(self):
        """Initialize Tickers with a logger."""
        self.logger = get_logger(self.__class__.__name__)

    def get_tickers(self):
        """Retrieve ticker data from SEC.gov company_tickers.json.

        Returns:
            Dictionary of ticker data from SEC.gov, or None on error.
        """
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            headers = {
                "User-Agent": "Company Name company@email.com",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            }
            response = requests.get(url, headers=headers)

            # Check if response is successful and is JSON
            if response.status_code != 200:
                self.logger.error(f"Failed to get tickers: HTTP {response.status_code}")
                self.logger.info(f"Response: {response.text[:500]}")
                return None

            # Check if the response is actually JSON
            content_type = response.headers.get("Content-Type", "")
            if "json" not in content_type.lower():
                self.logger.error(f"Response is not JSON. Content-Type: {content_type}")
                self.logger.info(f"Response: {response.text[:500]}")
                return None

            data = response.json()
            return data
        except Exception as e:
            self.logger.error(f"Failed to get tickers: {e}")
            return None


if __name__ == "__main__":
    foo = Tickers()
    tickers = foo.get_tickers()
    print(tickers)
