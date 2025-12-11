"""Shared fixtures for Redis tests.

All common fixtures, mocks, and test parameters are defined here
to reduce code duplication across test files.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_check_queues_logger():
    """Fixture to mock logger for check_queues."""
    with patch("system.algo_trader.redis.check_queues.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def mock_check_queues_queue_broker():
    """Fixture to mock QueueBroker for check_queues tests."""
    with patch("system.algo_trader.redis.check_queues.QueueBroker") as mock_queue_broker_class:
        mock_broker = MagicMock()
        mock_broker.get_queue_size.return_value = 0
        mock_broker.peek_queue.return_value = []
        mock_broker.get_data.return_value = None
        mock_queue_broker_class.return_value = mock_broker
        yield mock_broker
