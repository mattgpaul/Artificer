"""Shared fixtures for algo_trader domain tests.

This package-level conftest holds common mocks/fixtures so individual test modules
do not define `@pytest.fixture` or create inline mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from system.algo_trader.domain.engine import Engine
from system.algo_trader.ports.portfolio import PortfolioDecision


@pytest.fixture
def mock_clock() -> MagicMock:
    """Provide a mock clock with a stable `now()`."""
    clock = MagicMock()
    clock.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return clock


@pytest.fixture
def mock_strategy() -> MagicMock:
    """Provide a mock strategy that emits no intents."""
    strategy = MagicMock()
    strategy.on_market.return_value = []
    return strategy


@pytest.fixture
def mock_portfolio() -> MagicMock:
    """Provide a mock portfolio that returns an empty PortfolioDecision."""
    portfolio = MagicMock()
    portfolio.manage.return_value = PortfolioDecision(
        proposed_intents=(),
        final_intents=(),
        pause_until=None,
        audit=None,
    )
    return portfolio


@pytest.fixture
def mock_journal() -> MagicMock:
    """Provide a mock journal."""
    return MagicMock()


@pytest.fixture
def engine(
    mock_clock: MagicMock,
    mock_strategy: MagicMock,
    mock_portfolio: MagicMock,
    mock_journal: MagicMock,
) -> Engine:
    """Provide an Engine instance wired with mocks."""
    return Engine(
        clock=mock_clock,
        strategy=mock_strategy,
        portfolio=mock_portfolio,
        journal=mock_journal,
    )
