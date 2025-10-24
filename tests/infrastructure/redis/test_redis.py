"""Unit tests for BaseRedisClient - Redis Database Operations.

Tests cover client initialization, connection management, all Redis data types
(strings, hashes, sets, lists), TTL operations, and error handling.
All Redis operations are mocked to avoid requiring a Redis server.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.redis.redis import BaseRedisClient


class ConcreteRedisClient(BaseRedisClient):
    """Concrete implementation for testing abstract BaseRedisClient."""

    def _get_namespace(self) -> str:
        return "test_namespace"


class TestRedisClientInitialization:
    """Test BaseRedisClient initialization and configuration."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("infrastructure.redis.redis.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_initialization_default_config(self, mock_redis, mock_logger):
        """Test initialization with default configuration from environment."""
        with patch.dict(os.environ, {}, clear=True):
            client = ConcreteRedisClient()

            assert client.namespace == "test_namespace"
            assert client.host == "localhost"
            assert client.port == 6379
            assert client.db == 0
            assert client.max_connections == 10
            assert client.socket_timeout == 30

    def test_initialization_custom_config(self, mock_redis, mock_logger):
        """Test initialization with custom configuration from environment."""
        with patch.dict(
            os.environ,
            {
                "REDIS_HOST": "redis.example.com",
                "REDIS_PORT": "7000",
                "REDIS_DB": "5",
                "REDIS_MAX_CONNECTIONS": "20",
                "REDIS_SOCKET_TIMEOUT": "60",
            },
        ):
            client = ConcreteRedisClient()

            assert client.host == "redis.example.com"
            assert client.port == 7000
            assert client.db == 5
            assert client.max_connections == 20
            assert client.socket_timeout == 60

    def test_connection_pool_creation(self, mock_redis, mock_logger):
        """Test Redis connection pool is created correctly."""
        with patch.dict(os.environ, {}, clear=True):
            ConcreteRedisClient()

            mock_redis["module"].ConnectionPool.assert_called_once_with(
                host="localhost", port=6379, db=0, max_connections=10, socket_timeout=30
            )
            mock_redis["module"].Redis.assert_called_once()

    def test_connection_pool_creation_failure(self, mock_logger):
        """Test connection pool creation handles exceptions."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_redis_module.ConnectionPool.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                ConcreteRedisClient()

    def test_build_key(self, mock_redis, mock_logger):
        """Test key namespacing."""
        client = ConcreteRedisClient()

        namespaced_key = client._build_key("my_key")

        assert namespaced_key == "test_namespace:my_key"


class TestRedisClientStringOperations:
    """Test string get/set operations."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("infrastructure.redis.redis.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_get_success(self, mock_redis, mock_logger):
        """Test successful get operation."""
        mock_redis["client"].get.return_value = b"test_value"

        client = ConcreteRedisClient()
        result = client.get("test_key")

        assert result == "test_value"
        mock_redis["client"].get.assert_called_once_with("test_namespace:test_key")

    def test_get_nonexistent_key(self, mock_redis, mock_logger):
        """Test get operation for nonexistent key."""
        mock_redis["client"].get.return_value = None

        client = ConcreteRedisClient()
        result = client.get("missing_key")

        assert result is None

    def test_get_exception(self, mock_redis, mock_logger):
        """Test get operation handles exceptions."""
        mock_redis["client"].get.side_effect = Exception("Redis error")

        client = ConcreteRedisClient()
        result = client.get("error_key")

        assert result is None
        mock_logger.error.assert_called()

    def test_set_success(self, mock_redis, mock_logger):
        """Test successful set operation."""
        mock_redis["client"].set.return_value = True

        client = ConcreteRedisClient()
        result = client.set("test_key", "test_value")

        assert result is True
        mock_redis["client"].set.assert_called_once_with(
            "test_namespace:test_key", "test_value", ex=None
        )

    def test_set_with_ttl(self, mock_redis, mock_logger):
        """Test set operation with TTL."""
        mock_redis["client"].set.return_value = True

        client = ConcreteRedisClient()
        result = client.set("test_key", "test_value", ttl=300)

        assert result is True
        mock_redis["client"].set.assert_called_once_with(
            "test_namespace:test_key", "test_value", ex=300
        )

    def test_set_failure(self, mock_redis, mock_logger):
        """Test set operation failure."""
        mock_redis["client"].set.return_value = False

        client = ConcreteRedisClient()
        result = client.set("test_key", "test_value")

        assert result is False

    def test_set_exception(self, mock_redis, mock_logger):
        """Test set operation handles exceptions."""
        mock_redis["client"].set.side_effect = Exception("Redis error")

        client = ConcreteRedisClient()
        result = client.set("error_key", "value")

        assert result is False
        mock_logger.error.assert_called()


class TestRedisClientHashOperations:
    """Test hash operations (hget, hset, hgetall, hmset, hdel)."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("infrastructure.redis.redis.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_hget_success(self, mock_redis, mock_logger):
        """Test successful hget operation."""
        mock_redis["client"].hget.return_value = b"field_value"

        client = ConcreteRedisClient()
        result = client.hget("hash_key", "field_name")

        assert result == "field_value"
        mock_redis["client"].hget.assert_called_once_with("test_namespace:hash_key", "field_name")

    def test_hget_nonexistent_field(self, mock_redis, mock_logger):
        """Test hget for nonexistent field."""
        mock_redis["client"].hget.return_value = None

        client = ConcreteRedisClient()
        result = client.hget("hash_key", "missing_field")

        assert result is None

    def test_hget_exception(self, mock_redis, mock_logger):
        """Test hget handles exceptions."""
        mock_redis["client"].hget.side_effect = Exception("Redis error")

        client = ConcreteRedisClient()
        result = client.hget("hash_key", "field")

        assert result is None
        mock_logger.error.assert_called()

    def test_hset_success(self, mock_redis, mock_logger):
        """Test successful hset operation."""
        mock_redis["client"].hset.return_value = 1

        client = ConcreteRedisClient()
        result = client.hset("hash_key", "field", "value")

        assert result is True
        mock_redis["client"].hset.assert_called_once_with(
            "test_namespace:hash_key", "field", "value"
        )

    def test_hset_with_ttl(self, mock_redis, mock_logger):
        """Test hset operation with TTL."""
        mock_redis["client"].hset.return_value = 1

        client = ConcreteRedisClient()
        result = client.hset("hash_key", "field", "value", ttl=600)

        assert result is True
        mock_redis["client"].expire.assert_called_once_with("test_namespace:hash_key", 600)

    def test_hgetall_success(self, mock_redis, mock_logger):
        """Test successful hgetall operation."""
        mock_redis["client"].hgetall.return_value = {b"field1": b"value1", b"field2": b"value2"}

        client = ConcreteRedisClient()
        result = client.hgetall("hash_key")

        assert result == {"field1": "value1", "field2": "value2"}
        mock_redis["client"].hgetall.assert_called_once_with("test_namespace:hash_key")

    def test_hgetall_empty(self, mock_redis, mock_logger):
        """Test hgetall on empty hash."""
        mock_redis["client"].hgetall.return_value = {}

        client = ConcreteRedisClient()
        result = client.hgetall("empty_hash")

        assert result == {}

    def test_hgetall_exception(self, mock_redis, mock_logger):
        """Test hgetall handles exceptions."""
        mock_redis["client"].hgetall.side_effect = Exception("Redis error")

        client = ConcreteRedisClient()
        result = client.hgetall("hash_key")

        assert result == {}
        mock_logger.error.assert_called()

    def test_hmset_success(self, mock_redis, mock_logger):
        """Test successful hmset operation."""
        mock_redis["client"].hmset.return_value = True

        client = ConcreteRedisClient()
        mapping = {"field1": "value1", "field2": "value2"}
        result = client.hmset("hash_key", mapping)

        assert result is True
        mock_redis["client"].hmset.assert_called_once_with("test_namespace:hash_key", mapping)

    def test_hmset_with_ttl(self, mock_redis, mock_logger):
        """Test hmset operation with TTL."""
        mock_redis["client"].hmset.return_value = True

        client = ConcreteRedisClient()
        mapping = {"field1": "value1"}
        result = client.hmset("hash_key", mapping, ttl=300)

        assert result is True
        mock_redis["client"].expire.assert_called_once_with("test_namespace:hash_key", 300)

    def test_hdel_success(self, mock_redis, mock_logger):
        """Test successful hdel operation."""
        mock_redis["client"].hdel.return_value = 2

        client = ConcreteRedisClient()
        result = client.hdel("hash_key", "field1", "field2")

        assert result == 2
        mock_redis["client"].hdel.assert_called_once_with(
            "test_namespace:hash_key", "field1", "field2"
        )

    def test_hdel_nonexistent_fields(self, mock_redis, mock_logger):
        """Test hdel with nonexistent fields."""
        mock_redis["client"].hdel.return_value = 0

        client = ConcreteRedisClient()
        result = client.hdel("hash_key", "missing_field")

        assert result == 0

    def test_hdel_exception(self, mock_redis, mock_logger):
        """Test hdel handles exceptions."""
        mock_redis["client"].hdel.side_effect = Exception("Redis error")

        client = ConcreteRedisClient()
        result = client.hdel("hash_key", "field")

        assert result == 0
        mock_logger.error.assert_called()


class TestRedisClientJSONOperations:
    """Test JSON get/set operations."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("infrastructure.redis.redis.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_get_json_success(self, mock_redis, mock_logger):
        """Test successful get_json operation."""
        test_dict = {"key": "value", "number": 42}
        mock_redis["client"].get.return_value = json.dumps(test_dict).encode("utf-8")

        client = ConcreteRedisClient()
        result = client.get_json("json_key")

        assert result == test_dict

    def test_get_json_array(self, mock_redis, mock_logger):
        """Test get_json with array."""
        test_array = ["item1", "item2", "item3"]
        mock_redis["client"].get.return_value = json.dumps(test_array).encode("utf-8")

        client = ConcreteRedisClient()
        result = client.get_json("array_key")

        assert result == test_array

    def test_get_json_nonexistent(self, mock_redis, mock_logger):
        """Test get_json for nonexistent key."""
        mock_redis["client"].get.return_value = None

        client = ConcreteRedisClient()
        result = client.get_json("missing_key")

        assert result is None

    def test_get_json_invalid_json(self, mock_redis, mock_logger):
        """Test get_json with invalid JSON."""
        mock_redis["client"].get.return_value = b"not valid json"

        client = ConcreteRedisClient()
        result = client.get_json("invalid_json_key")

        assert result is None
        mock_logger.error.assert_called()

    def test_set_json_success(self, mock_redis, mock_logger):
        """Test successful set_json operation."""
        mock_redis["client"].set.return_value = True

        client = ConcreteRedisClient()
        test_dict = {"key": "value", "number": 42}
        result = client.set_json("json_key", test_dict)

        assert result is True
        # Verify JSON was serialized
        call_args = mock_redis["client"].set.call_args
        assert "test_namespace:json_key" in call_args[0]
        assert '"key"' in call_args[0][1]  # Check JSON format

    def test_set_json_with_ttl(self, mock_redis, mock_logger):
        """Test set_json operation with TTL."""
        mock_redis["client"].set.return_value = True

        client = ConcreteRedisClient()
        result = client.set_json("json_key", {"data": "value"}, ttl=120)

        assert result is True

    def test_set_json_array(self, mock_redis, mock_logger):
        """Test set_json with array."""
        mock_redis["client"].set.return_value = True

        client = ConcreteRedisClient()
        test_array = [1, 2, 3, 4, 5]
        result = client.set_json("array_key", test_array)

        assert result is True

    def test_set_json_exception(self, mock_redis, mock_logger):
        """Test set_json handles exceptions."""
        mock_redis["client"].set.side_effect = Exception("Redis error")

        client = ConcreteRedisClient()
        result = client.set_json("json_key", {"data": "value"})

        assert result is False
        mock_logger.error.assert_called()


class TestRedisClientSetOperations:
    """Test set operations (sadd, smembers, srem, sismember, scard)."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("infrastructure.redis.redis.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_sadd_success(self, mock_redis, mock_logger):
        """Test successful sadd operation."""
        mock_redis["client"].sadd.return_value = 2

        client = ConcreteRedisClient()
        result = client.sadd("set_key", "member1", "member2")

        assert result == 2
        mock_redis["client"].sadd.assert_called_once_with(
            "test_namespace:set_key", "member1", "member2"
        )

    def test_sadd_with_ttl(self, mock_redis, mock_logger):
        """Test sadd operation with TTL."""
        mock_redis["client"].sadd.return_value = 1

        client = ConcreteRedisClient()
        result = client.sadd("set_key", "member", ttl=180)

        assert result == 1
        mock_redis["client"].expire.assert_called_once_with("test_namespace:set_key", 180)

    def test_smembers_success(self, mock_redis, mock_logger):
        """Test successful smembers operation."""
        mock_redis["client"].smembers.return_value = {b"member1", b"member2", b"member3"}

        client = ConcreteRedisClient()
        result = client.smembers("set_key")

        assert result == {"member1", "member2", "member3"}

    def test_smembers_empty(self, mock_redis, mock_logger):
        """Test smembers on empty set."""
        mock_redis["client"].smembers.return_value = set()

        client = ConcreteRedisClient()
        result = client.smembers("empty_set")

        assert result == set()

    def test_srem_success(self, mock_redis, mock_logger):
        """Test successful srem operation."""
        mock_redis["client"].srem.return_value = 1

        client = ConcreteRedisClient()
        result = client.srem("set_key", "member")

        assert result == 1

    def test_sismember_exists(self, mock_redis, mock_logger):
        """Test sismember for existing member."""
        mock_redis["client"].sismember.return_value = True

        client = ConcreteRedisClient()
        result = client.sismember("set_key", "member")

        assert result is True

    def test_sismember_not_exists(self, mock_redis, mock_logger):
        """Test sismember for nonexistent member."""
        mock_redis["client"].sismember.return_value = False

        client = ConcreteRedisClient()
        result = client.sismember("set_key", "missing_member")

        assert result is False

    def test_scard_success(self, mock_redis, mock_logger):
        """Test successful scard operation."""
        mock_redis["client"].scard.return_value = 5

        client = ConcreteRedisClient()
        result = client.scard("set_key")

        assert result == 5


class TestRedisClientListOperations:
    """Test list operations (lpush, rpush, lpop, rpop, llen, lrange)."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("infrastructure.redis.redis.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_lpush_success(self, mock_redis, mock_logger):
        """Test successful lpush operation."""
        mock_redis["client"].lpush.return_value = 3

        client = ConcreteRedisClient()
        result = client.lpush("list_key", "value1", "value2")

        assert result == 3
        mock_redis["client"].lpush.assert_called_once_with(
            "test_namespace:list_key", "value1", "value2"
        )

    def test_lpush_with_ttl(self, mock_redis, mock_logger):
        """Test lpush operation with TTL."""
        mock_redis["client"].lpush.return_value = 1

        client = ConcreteRedisClient()
        result = client.lpush("list_key", "value", ttl=240)

        assert result == 1
        mock_redis["client"].expire.assert_called_once_with("test_namespace:list_key", 240)

    def test_rpush_success(self, mock_redis, mock_logger):
        """Test successful rpush operation."""
        mock_redis["client"].rpush.return_value = 2

        client = ConcreteRedisClient()
        result = client.rpush("list_key", "value")

        assert result == 2

    def test_lpop_success(self, mock_redis, mock_logger):
        """Test successful lpop operation."""
        mock_redis["client"].lpop.return_value = b"popped_value"

        client = ConcreteRedisClient()
        result = client.lpop("list_key")

        assert result == "popped_value"

    def test_lpop_empty_list(self, mock_redis, mock_logger):
        """Test lpop on empty list."""
        mock_redis["client"].lpop.return_value = None

        client = ConcreteRedisClient()
        result = client.lpop("empty_list")

        assert result is None

    def test_rpop_success(self, mock_redis, mock_logger):
        """Test successful rpop operation."""
        mock_redis["client"].rpop.return_value = b"last_value"

        client = ConcreteRedisClient()
        result = client.rpop("list_key")

        assert result == "last_value"

    def test_llen_success(self, mock_redis, mock_logger):
        """Test successful llen operation."""
        mock_redis["client"].llen.return_value = 10

        client = ConcreteRedisClient()
        result = client.llen("list_key")

        assert result == 10

    def test_lrange_success(self, mock_redis, mock_logger):
        """Test successful lrange operation."""
        mock_redis["client"].lrange.return_value = [b"item1", b"item2", b"item3"]

        client = ConcreteRedisClient()
        result = client.lrange("list_key", 0, -1)

        assert result == ["item1", "item2", "item3"]
        mock_redis["client"].lrange.assert_called_once_with("test_namespace:list_key", 0, -1)

    def test_lrange_partial(self, mock_redis, mock_logger):
        """Test lrange with partial range."""
        mock_redis["client"].lrange.return_value = [b"item2", b"item3"]

        client = ConcreteRedisClient()
        result = client.lrange("list_key", 1, 2)

        assert result == ["item2", "item3"]


class TestRedisClientUtilityOperations:
    """Test utility operations (ping, exists, delete, expire, ttl, keys, flushdb)."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("infrastructure.redis.redis.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_ping_success(self, mock_redis, mock_logger):
        """Test successful ping operation."""
        mock_redis["client"].ping.return_value = True

        client = ConcreteRedisClient()
        result = client.ping()

        assert result is True

    def test_ping_failure(self, mock_redis, mock_logger):
        """Test ping failure."""
        mock_redis["client"].ping.side_effect = Exception("Connection refused")

        client = ConcreteRedisClient()
        result = client.ping()

        assert result is False
        mock_logger.error.assert_called()

    def test_exists_true(self, mock_redis, mock_logger):
        """Test exists for existing key."""
        mock_redis["client"].exists.return_value = 1

        client = ConcreteRedisClient()
        result = client.exists("existing_key")

        assert result is True

    def test_exists_false(self, mock_redis, mock_logger):
        """Test exists for nonexistent key."""
        mock_redis["client"].exists.return_value = 0

        client = ConcreteRedisClient()
        result = client.exists("missing_key")

        assert result is False

    def test_delete_success(self, mock_redis, mock_logger):
        """Test successful delete operation."""
        mock_redis["client"].delete.return_value = 1

        client = ConcreteRedisClient()
        result = client.delete("key_to_delete")

        assert result is True

    def test_delete_nonexistent(self, mock_redis, mock_logger):
        """Test delete nonexistent key."""
        mock_redis["client"].delete.return_value = 0

        client = ConcreteRedisClient()
        result = client.delete("missing_key")

        assert result is False

    def test_expire_success(self, mock_redis, mock_logger):
        """Test successful expire operation."""
        mock_redis["client"].expire.return_value = True

        client = ConcreteRedisClient()
        result = client.expire("key", 60)

        assert result is True
        mock_redis["client"].expire.assert_called_once_with("test_namespace:key", 60)

    def test_ttl_has_expiration(self, mock_redis, mock_logger):
        """Test ttl for key with expiration."""
        mock_redis["client"].ttl.return_value = 120

        client = ConcreteRedisClient()
        result = client.ttl("key")

        assert result == 120

    def test_ttl_no_expiration(self, mock_redis, mock_logger):
        """Test ttl for key without expiration."""
        mock_redis["client"].ttl.return_value = -1

        client = ConcreteRedisClient()
        result = client.ttl("key")

        assert result == -1

    def test_ttl_key_not_exists(self, mock_redis, mock_logger):
        """Test ttl for nonexistent key."""
        mock_redis["client"].ttl.return_value = -2

        client = ConcreteRedisClient()
        result = client.ttl("missing_key")

        assert result == -2

    def test_keys_success(self, mock_redis, mock_logger):
        """Test successful keys operation."""
        mock_redis["client"].keys.return_value = [
            b"test_namespace:key1",
            b"test_namespace:key2",
            b"test_namespace:key3",
        ]

        client = ConcreteRedisClient()
        result = client.keys("*")

        assert result == ["key1", "key2", "key3"]

    def test_keys_pattern(self, mock_redis, mock_logger):
        """Test keys with specific pattern."""
        mock_redis["client"].keys.return_value = [
            b"test_namespace:user:1",
            b"test_namespace:user:2",
        ]

        client = ConcreteRedisClient()
        result = client.keys("user:*")

        assert result == ["user:1", "user:2"]

    def test_flushdb_success(self, mock_redis, mock_logger):
        """Test successful flushdb operation."""
        mock_redis["client"].flushdb.return_value = True

        client = ConcreteRedisClient()
        result = client.flushdb()

        assert result is True
        mock_logger.warning.assert_called()

    def test_flushdb_failure(self, mock_redis, mock_logger):
        """Test flushdb failure."""
        mock_redis["client"].flushdb.side_effect = Exception("Permission denied")

        client = ConcreteRedisClient()
        result = client.flushdb()

        assert result is False


class TestRedisClientPipelineOperations:
    """Test pipeline operations."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()
            mock_pipeline = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client
            mock_client.pipeline.return_value = mock_pipeline

            yield {
                "module": mock_redis_module,
                "pool": mock_pool,
                "client": mock_client,
                "pipeline": mock_pipeline,
            }

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("infrastructure.redis.redis.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_pipeline_execute_success(self, mock_redis, mock_logger):
        """Test successful pipeline execution."""
        mock_redis["pipeline"].execute.return_value = [True, True, True]

        client = ConcreteRedisClient()
        operations = [
            ("set", "key1", "value1"),
            ("set", "key2", "value2"),
            ("set", "key3", "value3"),
        ]
        result = client.pipeline_execute(operations)

        assert result is True
        mock_redis["pipeline"].execute.assert_called_once()

    def test_pipeline_execute_partial_failure(self, mock_redis, mock_logger):
        """Test pipeline execution with some failures."""
        mock_redis["pipeline"].execute.return_value = [True, False, True]

        client = ConcreteRedisClient()
        operations = [
            ("set", "key1", "value1"),
            ("set", "key2", "value2"),
            ("set", "key3", "value3"),
        ]
        result = client.pipeline_execute(operations)

        assert result is False

    def test_pipeline_execute_exception(self, mock_redis, mock_logger):
        """Test pipeline execution handles exceptions."""
        mock_redis["pipeline"].execute.side_effect = Exception("Pipeline error")

        client = ConcreteRedisClient()
        operations = [("set", "key", "value")]
        result = client.pipeline_execute(operations)

        assert result is False
        mock_logger.error.assert_called()


class TestRedisClientIntegration:
    """Test integration scenarios with multiple operations."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture to mock Redis connection."""
        with patch("infrastructure.redis.redis.redis") as mock_redis_module:
            mock_pool = MagicMock()
            mock_client = MagicMock()

            mock_redis_module.ConnectionPool.return_value = mock_pool
            mock_redis_module.Redis.return_value = mock_client

            yield {"module": mock_redis_module, "pool": mock_pool, "client": mock_client}

    @pytest.fixture
    def mock_logger(self):
        """Fixture to mock logger."""
        with patch("infrastructure.redis.redis.get_logger") as mock_get_logger:
            mock_logger_instance = MagicMock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance

    def test_user_session_workflow(self, mock_redis, mock_logger):
        """Test complete user session workflow."""
        # Mock responses
        mock_redis["client"].set.return_value = True
        mock_redis["client"].get.return_value = json.dumps({"user_id": "123"}).encode("utf-8")
        mock_redis["client"].exists.return_value = 1
        mock_redis["client"].delete.return_value = 1

        client = ConcreteRedisClient()

        # Set session
        session_data = {"user_id": "123", "username": "test_user"}
        assert client.set_json("session:abc123", session_data, ttl=3600)

        # Get session
        retrieved_session = client.get_json("session:abc123")
        assert retrieved_session is not None

        # Check exists
        assert client.exists("session:abc123")

        # Delete session
        assert client.delete("session:abc123")

    def test_cache_workflow(self, mock_redis, mock_logger):
        """Test cache set and retrieval workflow."""
        mock_redis["client"].set.return_value = True
        mock_redis["client"].get.return_value = b"cached_value"
        mock_redis["client"].ttl.return_value = 300

        client = ConcreteRedisClient()

        # Set cache with TTL
        assert client.set("cache:data", "cached_value", ttl=600)

        # Get from cache
        assert client.get("cache:data") == "cached_value"

        # Check TTL
        ttl = client.ttl("cache:data")
        assert ttl > 0
