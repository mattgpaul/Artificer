"""Configuration models for infrastructure components.

Provides Pydantic-based configuration classes for Redis and InfluxDB
that can be used across all systems in the monorepo.
"""

from __future__ import annotations

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisConfig(BaseSettings):
    """Redis connection configuration with environment variable support.

    Reads from REDIS_* environment variables automatically.

    Attributes:
        host: Redis server hostname.
        port: Redis server port.
        db: Redis database number.
        max_connections: Maximum connection pool size.
        socket_timeout: Socket timeout in seconds.
    """

    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    max_connections: int = Field(default=10)
    socket_timeout: int = Field(default=30)

    class Config:
        """Configuration for Pydantic BaseSettings."""

        env_prefix = "REDIS_"


class InfluxDBConfig(BaseSettings):
    """InfluxDB connection configuration with environment variable support.

    Reads from INFLUXDB* environment variables automatically.
    Supports both INFLUXDB3_HTTP_BIND_ADDR (host:port format) and
    separate INFLUXDB_HOST/INFLUXDB_PORT variables.

    Attributes:
        host: InfluxDB server hostname.
        port: InfluxDB server port.
        token: Authentication token (from INFLUXDB3_AUTH_TOKEN).
        database: Target database name (from INFLUXDB_DATABASE).
    """

    model_config = SettingsConfigDict(
        env_file=None,  # Explicitly disable env file loading
        extra="ignore",
    )

    host: str = Field(default="localhost")
    port: int = Field(default=8181)
    token: str = Field(default="my-secret-token")
    database: str = Field(default="")

    def __init__(self, **kwargs):
        """Initialize InfluxDBConfig with custom env var handling."""
        # Read from environment if not provided in kwargs
        if "host" not in kwargs:
            bind_addr = os.getenv("INFLUXDB3_HTTP_BIND_ADDR")
            if bind_addr and ":" in bind_addr:
                kwargs["host"], kwargs["port"] = bind_addr.split(":", 1)
                kwargs["port"] = int(kwargs["port"])
            else:
                host_val = os.getenv("INFLUXDB_HOST")
                if host_val:
                    kwargs["host"] = host_val
                port_val = os.getenv("INFLUXDB_PORT")
                if port_val:
                    kwargs["port"] = int(port_val)

        if "token" not in kwargs:
            token_val = os.getenv("INFLUXDB3_AUTH_TOKEN")
            if token_val:
                kwargs["token"] = token_val

        if "database" not in kwargs:
            db_val = os.getenv("INFLUXDB_DATABASE")
            if db_val:
                kwargs["database"] = db_val

        super().__init__(**kwargs)

    @classmethod
    def from_env(cls) -> InfluxDBConfig:
        """Create config from environment variables.

        Handles special case of INFLUXDB3_HTTP_BIND_ADDR format (host:port).
        """
        return cls()


class ThreadConfig(BaseSettings):
    """Thread manager configuration with environment variable support.

    Reads from THREAD_* environment variables automatically.

    Attributes:
        daemon_threads: Whether threads should be daemon threads.
        max_threads: Maximum number of concurrent threads allowed.
        thread_timeout: Default timeout for thread operations in seconds.
    """

    daemon_threads: bool = Field(default=True)
    max_threads: int = Field(default=10)
    thread_timeout: int = Field(default=30)

    model_config = SettingsConfigDict(
        env_prefix="THREAD_",
        env_file=None,
    )
