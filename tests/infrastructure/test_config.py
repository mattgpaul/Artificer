"""Unit tests for Configuration Models - Infrastructure Components.

Tests cover RedisConfig, InfluxDBConfig, ThreadConfig, and SQLiteConfig
initialization, environment variable handling, and default values.
"""

import os
from unittest.mock import patch

from infrastructure.config import (
    InfluxDBConfig,
    RedisConfig,
    SQLiteConfig,
    ThreadConfig,
)


class TestSQLiteConfig:
    """Test SQLiteConfig initialization and configuration."""

    def test_sqlite_config_defaults(self):
        """Test SQLiteConfig uses default values when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            config = SQLiteConfig()

            assert config.db_path == ":memory:"
            assert config.timeout == 30
            assert config.isolation_level == "DEFERRED"

    def test_sqlite_config_from_env_vars(self):
        """Test SQLiteConfig reads from environment variables."""
        with patch.dict(
            os.environ,
            {
                "SQLITE_DB_PATH": "/tmp/test.db",
                "SQLITE_TIMEOUT": "60",
                "SQLITE_ISOLATION_LEVEL": "IMMEDIATE",
            },
        ):
            config = SQLiteConfig()

            assert config.db_path == "/tmp/test.db"
            assert config.timeout == 60
            assert config.isolation_level == "IMMEDIATE"

    def test_sqlite_config_custom_values(self):
        """Test SQLiteConfig accepts custom values."""
        config = SQLiteConfig(db_path="/custom/path.db", timeout=45, isolation_level="EXCLUSIVE")

        assert config.db_path == "/custom/path.db"
        assert config.timeout == 45
        assert config.isolation_level == "EXCLUSIVE"

    def test_sqlite_config_env_prefix(self):
        """Test SQLiteConfig uses SQLITE_ prefix for environment variables."""
        with patch.dict(
            os.environ,
            {
                "SQLITE_DB_PATH": "/env/path.db",
                "SQLITE_TIMEOUT": "90",
            },
        ):
            config = SQLiteConfig()

            assert config.db_path == "/env/path.db"
            assert config.timeout == 90

    def test_sqlite_config_isolation_levels(self):
        """Test SQLiteConfig accepts different isolation levels."""
        for isolation_level in ["DEFERRED", "IMMEDIATE", "EXCLUSIVE"]:
            config = SQLiteConfig(isolation_level=isolation_level)
            assert config.isolation_level == isolation_level

    def test_sqlite_config_timeout_types(self):
        """Test SQLiteConfig handles timeout as integer."""
        config = SQLiteConfig(timeout=30)
        assert isinstance(config.timeout, int)
        assert config.timeout == 30

    def test_sqlite_config_memory_database(self):
        """Test SQLiteConfig supports in-memory database."""
        config = SQLiteConfig(db_path=":memory:")
        assert config.db_path == ":memory:"


class TestRedisConfig:
    """Test RedisConfig initialization and configuration."""

    def test_redis_config_defaults(self):
        """Test RedisConfig uses default values when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            config = RedisConfig()

            assert config.host == "localhost"
            assert config.port == 6379
            assert config.db == 0
            assert config.max_connections == 10
            assert config.socket_timeout == 30

    def test_redis_config_from_env_vars(self):
        """Test RedisConfig reads from environment variables."""
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
            config = RedisConfig()

            assert config.host == "redis.example.com"
            assert config.port == 7000
            assert config.db == 5
            assert config.max_connections == 20
            assert config.socket_timeout == 60


class TestInfluxDBConfig:
    """Test InfluxDBConfig initialization and configuration."""

    def test_influxdb_config_defaults(self):
        """Test InfluxDBConfig uses default values when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            config = InfluxDBConfig()

            assert config.host == "localhost"
            assert config.port == 8181
            assert config.token == "my-secret-token"
            assert config.database == ""

    def test_influxdb_config_from_separate_env_vars(self):
        """Test InfluxDBConfig reads from separate host/port env vars."""
        with patch.dict(
            os.environ,
            {
                "INFLUXDB_HOST": "influx.example.com",
                "INFLUXDB_PORT": "9000",
                "INFLUXDB3_AUTH_TOKEN": "custom-token",
                "INFLUXDB_DATABASE": "testdb",
            },
        ):
            config = InfluxDBConfig()

            assert config.host == "influx.example.com"
            assert config.port == 9000
            assert config.token == "custom-token"
            assert config.database == "testdb"

    def test_influxdb_config_from_bind_addr(self):
        """Test InfluxDBConfig reads from INFLUXDB3_HTTP_BIND_ADDR format."""
        with patch.dict(
            os.environ,
            {
                "INFLUXDB3_HTTP_BIND_ADDR": "influx.example.com:8086",
                "INFLUXDB3_AUTH_TOKEN": "token123",
                "INFLUXDB_DATABASE": "mydb",
            },
        ):
            config = InfluxDBConfig()

            assert config.host == "influx.example.com"
            assert config.port == 8086
            assert config.token == "token123"
            assert config.database == "mydb"


class TestThreadConfig:
    """Test ThreadConfig initialization and configuration."""

    def test_thread_config_defaults(self):
        """Test ThreadConfig uses default values when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            config = ThreadConfig()

            assert config.daemon_threads is True
            assert config.max_threads == 10
            assert config.thread_timeout == 30

    def test_thread_config_from_env_vars(self):
        """Test ThreadConfig reads from environment variables."""
        with patch.dict(
            os.environ,
            {
                "THREAD_DAEMON_THREADS": "false",
                "THREAD_MAX_THREADS": "20",
                "THREAD_THREAD_TIMEOUT": "60",
            },
        ):
            config = ThreadConfig()

            assert config.daemon_threads is False
            assert config.max_threads == 20
            assert config.thread_timeout == 60
