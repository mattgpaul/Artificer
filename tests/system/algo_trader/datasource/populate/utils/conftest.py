"""Shared fixtures for populate utils tests."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def auto_mock_external_calls():
    """Automatically mock external calls to prevent hangs."""
    # Don't auto-mock here - let individual tests control mocking
    yield


@pytest.fixture
def mock_influx_client():
    """Fixture to mock MarketDataInflux client."""
    with patch(
        "system.algo_trader.datasource.populate.utils.market_cap.MarketDataInflux"
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_company_facts_df():
    """Fixture to create sample company facts DataFrame."""
    dates = pd.date_range("2023-01-01", periods=4, freq="QE", tz="UTC")
    df = pd.DataFrame(
        {
            "shares_outstanding": [1000000, 1100000, 1200000, 1300000],
            "revenue": [10000000, 11000000, 12000000, 13000000],
        },
        index=dates,
    )
    return df


@pytest.fixture
def mock_logger():
    """Fixture to mock logger."""
    with patch(
        "system.algo_trader.datasource.populate.utils.market_cap.get_logger"
    ) as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance
