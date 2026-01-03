"""Bad ticker verifier for OHLCV data.

This module provides functionality to verify and remove tickers from the
bad tickers list if they now have valid data.
"""

from infrastructure.logging.logger import get_logger
from system.algo_trader.mysql.bad_ticker_client import BadTickerClient
from system.algo_trader.schwab.market_handler import MarketHandler
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


class BadTickerVerifier:
    """Verifier for bad tickers in MySQL database.

    Checks if tickers marked as bad now have valid price history data and
    removes them from the bad tickers list if so. Returns list of recovered
    tickers for processing.
    """

    def __init__(self, logger=None):
        """Initialize bad ticker verifier.

        Args:
            logger: Optional logger instance. If not provided, creates a new one.
        """
        self.logger = logger or get_logger(self.__class__.__name__)

    def verify_bad_tickers(
        self,
        frequency_type: FrequencyType,
        frequency_value: int,
        period_type: PeriodType,
        period_value: int,
    ) -> list[str]:
        """Verify bad tickers and remove those with valid data.

        Checks each bad ticker to see if it now has valid price history data.
        If valid data is found, the ticker is removed from the bad_tickers list
        and added to the returned list for processing.

        Args:
            frequency_type: Frequency type for price history check.
            frequency_value: Frequency value for price history check.
            period_type: Period type for price history check.
            period_value: Period value for price history check.

        Returns:
            List of ticker symbols that were found to have valid data and
            removed from bad_tickers. These should be processed by OHLCVProcessor.
        """
        self.logger.info("Starting verification of bad tickers in MySQL...")
        bad_ticker_client = BadTickerClient()
        market_handler = MarketHandler()

        recovered_tickers = []

        try:
            bad_tickers = bad_ticker_client.get_bad_tickers(limit=10000)
            if not bad_tickers:
                self.logger.info("No bad tickers found in MySQL")
                return recovered_tickers

            self.logger.info(f"Found {len(bad_tickers)} bad tickers to verify")
            removed_count = 0
            still_bad_count = 0
            error_count = 0

            for bad_ticker_record in bad_tickers:
                ticker = bad_ticker_record.get("ticker")
                if not ticker:
                    continue

                try:
                    response = market_handler.get_price_history(
                        ticker=ticker,
                        period_type=period_type,
                        period=period_value,
                        frequency_type=frequency_type,
                        frequency=frequency_value,
                    )

                    if (
                        response
                        and "candles" in response
                        and response["candles"]
                        and len(response["candles"]) > 0
                    ):
                        # Remove from bad_tickers if valid data found
                        if bad_ticker_client.remove_bad_ticker(ticker):
                            self.logger.info(
                                f"Removed {ticker} from bad_tickers (now has valid data)"
                            )
                            recovered_tickers.append(ticker)
                            removed_count += 1
                        else:
                            self.logger.error(f"Failed to remove {ticker} from bad_tickers")
                            error_count += 1
                    else:
                        still_bad_count += 1
                        self.logger.debug(f"{ticker} is still bad")

                except Exception as e:
                    self.logger.error(f"Error verifying ticker {ticker}: {e}")
                    error_count += 1

            self.logger.info(
                f"Verification complete: {removed_count} removed, "
                f"{still_bad_count} still bad, {error_count} errors"
            )

            if recovered_tickers:
                self.logger.info(
                    f"Found {len(recovered_tickers)} \
                        recovered tickers to process: {recovered_tickers}"
                )

        except Exception as e:
            self.logger.error(f"Error during bad ticker verification: {e}")

        return recovered_tickers
