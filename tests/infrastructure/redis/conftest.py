"""Shared fixtures for Redis infrastructure tests.

All external Redis interactions are mocked so tests can run without a real
Redis server. Fixtures here are reused across all Redis client tests.
"""

from __future__ import annotations

from typing import Any, Dict

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def redis_mocks() -> Dict[str, Any]:
    """Mock the `redis` client and logger used by the Redis base client.

    Provides:
    - redis_module: patched low-level `redis` module
    - pool: mocked ConnectionPool instance
    - client: mocked Redis client instance
    - logger: mocked logger instance
    """
    with patch("infrastructure.redis.base_redis_client.redis") as mock_redis_module, patch(
        "infrastructure.redis.base_redis_client.get_logger",
    ) as mock_get_logger:
        mock_pool = MagicMock()
        mock_client = MagicMock()

        mock_redis_module.ConnectionPool.return_value = mock_pool
        mock_redis_module.Redis.return_value = mock_client

        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        yield {
            "redis_module": mock_redis_module,
            "pool": mock_pool,
            "client": mock_client,
            "logger": mock_logger_instance,
        }


