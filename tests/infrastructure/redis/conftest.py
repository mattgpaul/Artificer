"""Shared fixtures for Redis stream wrapper tests."""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.redis.redis import BaseRedisClient


class StreamRedisClient(BaseRedisClient):
    """Concrete implementation for stream wrapper tests."""

    def _get_namespace(self) -> str:
        return "test_namespace"


@pytest.fixture
def stream_mock_redis():
    """Fixture to mock Redis connection for stream tests."""
    with patch("infrastructure.redis.redis.redis") as mock_redis_module:
        mock_pool = MagicMock()
        mock_client = MagicMock()

        mock_redis_module.ConnectionPool.return_value = mock_pool
        mock_redis_module.Redis.return_value = mock_client

        yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}


@pytest.fixture
def stream_mock_logger():
    """Fixture to mock logger for stream tests."""
    with patch("infrastructure.redis.redis.get_logger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def stream_client(stream_mock_redis, stream_mock_logger):
    """Fixture to provide a stream-ready Redis client and mocks."""
    client = StreamRedisClient()
    return {"client": client, "redis": stream_mock_redis, "logger": stream_mock_logger}

