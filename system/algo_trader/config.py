"""Configuration models for algo_trader system.

Provides system-specific configuration including Schwab API credentials
and overall system config that composes infrastructure configs.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings

from infrastructure.config import InfluxDBConfig, RedisConfig


class SchwabConfig(BaseSettings):
    """Schwab API configuration with environment variable support.

    Reads from SCHWAB_* environment variables automatically.

    Attributes:
        app_name: Schwab application name.
        api_key: Schwab API key.
        secret: Schwab API secret.
        refresh_token: OAuth refresh token.
    """

    app_name: str = Field(default="")
    api_key: str = Field(default="")
    secret: str = Field(default="")
    refresh_token: str = Field(default="")

    class Config:
        """Configuration for Pydantic BaseSettings."""

        env_prefix = "SCHWAB_"


class AlgoTraderConfig(BaseSettings):
    """Complete algo_trader system configuration.

    Composes infrastructure and system-specific configurations.
    Can be created from environment variables or explicitly provided.

    Attributes:
        redis: Redis configuration.
        influxdb: InfluxDB configuration.
        schwab: Schwab API configuration.
        log_level: Logging level.
    """

    redis: RedisConfig = Field(default_factory=RedisConfig)
    influxdb: InfluxDBConfig = Field(default_factory=InfluxDBConfig.from_env)
    schwab: SchwabConfig = Field(default_factory=SchwabConfig)
    log_level: str = Field(default="INFO")

    @classmethod
    def from_env(cls) -> AlgoTraderConfig:
        """Create complete config from environment variables.

        Returns:
            AlgoTraderConfig with all sub-configs populated from environment.
        """
        return cls(
            redis=RedisConfig(),
            influxdb=InfluxDBConfig.from_env(),
            schwab=SchwabConfig(),
        )
