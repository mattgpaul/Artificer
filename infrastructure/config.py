"""Configuration models for infrastructure components.

Provides Pydantic-based configuration classes for Redis and InfluxDB
that can be used across all systems in the monorepo.
"""

from __future__ import annotations

import os
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings


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

    host: str = Field(default="localhost")
    port: int = Field(default=8181)
    token: str = Field(default="my-secret-token")
    database: str = Field(default="")

    class Config:
        """Configuration for Pydantic BaseSettings with custom env var names."""

        # Custom env var names
        fields: ClassVar[dict[str, dict[str, str]]] = {
            "token": {"env": "INFLUXDB3_AUTH_TOKEN"},
            "database": {"env": "INFLUXDB_DATABASE"},
            "host": {"env": "INFLUXDB_HOST"},
            "port": {"env": "INFLUXDB_PORT"},
        }

    @classmethod
    def from_env(cls) -> InfluxDBConfig:
        """Create config from environment variables.

        Handles special case of INFLUXDB3_HTTP_BIND_ADDR format (host:port).
        """
        # Check for bind addr format first
        bind_addr = os.getenv("INFLUXDB3_HTTP_BIND_ADDR")
        if bind_addr and ":" in bind_addr:
            host, port = bind_addr.split(":", 1)
            return cls(
                host=host,
                port=int(port),
                token=os.getenv("INFLUXDB3_AUTH_TOKEN", ""),
                database=os.getenv("INFLUXDB_DATABASE", ""),
            )
        # Otherwise use standard parsing
        return cls()
