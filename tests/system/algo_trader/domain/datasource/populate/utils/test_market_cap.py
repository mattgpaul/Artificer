"""Unit tests for market_cap - Market Cap Calculation.

Tests cover market cap calculation from company facts and OHLCV data.
All external dependencies are mocked via conftest.py.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from system.algo_trader.datasource.populate.utils.market_cap import calculate_market_cap


class TestCalculateMarketCap:
    """Test market cap calculation."""

    def test_calculate_market_cap_success(self, mock_influx_client, sample_company_facts_df):
        """Test successful market cap calculation."""
        ticker = "AAPL"
        ohlcv_data = pd.DataFrame(
            {
                "close": [150.0, 160.0, 170.0, 180.0],
            },
            index=sample_company_facts_df.index,
        )

        mock_influx_client.query.return_value = ohlcv_data

        result = calculate_market_cap(sample_company_facts_df, ticker, mock_influx_client)

        assert "market_cap" in result.columns
        assert result.loc[sample_company_facts_df.index[0], "market_cap"] == 1000000 * 150.0
        mock_influx_client.query.assert_called_once()

    def test_calculate_market_cap_no_shares_outstanding(self, mock_influx_client, mock_logger):
        """Test market cap calculation when shares_outstanding column is missing."""
        ticker = "AAPL"
        df = pd.DataFrame(
            {
                "revenue": [10000000, 11000000],
            },
            index=pd.date_range("2023-01-01", periods=2, freq="QE", tz="UTC"),
        )

        result = calculate_market_cap(df, ticker, mock_influx_client)

        assert "market_cap" in result.columns
        assert result["market_cap"].isna().all()
        mock_logger.warning.assert_called()

    @pytest.mark.parametrize(
        "ohlcv_result,expected_all_na",
        [
            (None, True),
            (pd.DataFrame(), True),
        ],
    )
    def test_calculate_market_cap_no_ohlcv_data(
        self,
        mock_influx_client,
        sample_company_facts_df,
        mock_logger,
        ohlcv_result,
        expected_all_na,
    ):
        """Test market cap calculation when no OHLCV data is available."""
        ticker = "AAPL"
        mock_influx_client.query.return_value = ohlcv_result

        result = calculate_market_cap(sample_company_facts_df, ticker, mock_influx_client)

        assert "market_cap" in result.columns
        assert result["market_cap"].isna().all() == expected_all_na
        mock_logger.warning.assert_called()

    def test_calculate_market_cap_creates_default_client(self, sample_company_facts_df):
        """Test market cap calculation creates default InfluxDB client when None provided."""
        ticker = "AAPL"
        ohlcv_data = pd.DataFrame(
            {
                "close": [150.0],
            },
            index=[sample_company_facts_df.index[0]],
        )

        with (
            patch(
                "system.algo_trader.datasource.populate.utils.market_cap.MarketDataInflux"
            ) as mock_client_class,
            patch("system.algo_trader.datasource.populate.utils.market_cap.get_logger"),
        ):
            mock_client = MagicMock()
            mock_client.query.return_value = ohlcv_data
            mock_client_class.return_value = mock_client

            result = calculate_market_cap(sample_company_facts_df, ticker, None)

            assert "market_cap" in result.columns
            mock_client_class.assert_called_once()

    def test_calculate_market_cap_handles_missing_prices(
        self, mock_influx_client, sample_company_facts_df
    ):
        """Test market cap calculation handles missing prices gracefully."""
        ticker = "AAPL"
        # OHLCV data with some missing prices
        ohlcv_data = pd.DataFrame(
            {
                "close": [150.0, pd.NA, 170.0, 180.0],
            },
            index=sample_company_facts_df.index,
        )

        mock_influx_client.query.return_value = ohlcv_data

        result = calculate_market_cap(sample_company_facts_df, ticker, mock_influx_client)

        assert "market_cap" in result.columns
        # First period should have market cap
        assert pd.notna(result.loc[sample_company_facts_df.index[0], "market_cap"])

    def test_calculate_market_cap_exception_handling(
        self, mock_influx_client, sample_company_facts_df, mock_logger
    ):
        """Test market cap calculation handles exceptions gracefully."""
        ticker = "AAPL"
        mock_influx_client.query.side_effect = Exception("Database error")

        result = calculate_market_cap(sample_company_facts_df, ticker, mock_influx_client)

        assert "market_cap" in result.columns
        assert result["market_cap"].isna().all()
        mock_logger.error.assert_called()

    def test_calculate_market_cap_with_time_column(
        self, mock_influx_client, sample_company_facts_df
    ):
        """Test market cap calculation when OHLCV has 'time' column instead of index."""
        ticker = "AAPL"
        ohlcv_data = pd.DataFrame(
            {
                "time": sample_company_facts_df.index,
                "close": [150.0, 160.0, 170.0, 180.0],
            },
        )

        mock_influx_client.query.return_value = ohlcv_data

        result = calculate_market_cap(sample_company_facts_df, ticker, mock_influx_client)

        assert "market_cap" in result.columns
        assert pd.notna(result["market_cap"]).any()
