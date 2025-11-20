"""Pydantic schemas for backtest results payloads.

These models validate the structure of backtest trades and metrics payloads
before they are enqueued into Redis. This provides a strict contract between
the backtest layer and the InfluxDB publisher, reducing the chance of
invalid or inconsistent data reaching InfluxDB.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator


class BacktestTimeSeriesData(BaseModel):
    """Generic time-series payload used for backtest trades and metrics.

    The payload is a column-oriented dictionary where each key maps to a list
    of values. The ``datetime`` column is required and must contain millisecond
    timestamps. All other list-valued columns must have the same length as
    ``datetime`` to ensure a consistent tabular shape for InfluxDB writes.
    """

    # Allow dynamic columns in addition to the required datetime column.
    model_config = ConfigDict(extra="allow")

    datetime: list[int]

    @field_validator("datetime")
    @classmethod
    def validate_datetime(cls, value: list[int]) -> list[int]:
        """Validate datetime list contains integers and is non-empty."""
        if not value:
            raise ValueError("datetime array must not be empty")
        # Coerce all values to int and ensure they are non-negative.
        coerced: list[int] = []
        for v in value:
            try:
                iv = int(v)
            except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
                raise ValueError(f"Invalid datetime value {v!r}") from exc
            if iv < 0:
                raise ValueError("datetime values must be non-negative millisecond timestamps")
            coerced.append(iv)
        return coerced

    @model_validator(mode="after")
    def validate_column_lengths(self) -> "BacktestTimeSeriesData":
        """Ensure all list-valued columns have the same length as datetime."""
        expected_len = len(self.datetime)

        # Pydantic v2 stores dynamically allowed extra fields in __pydantic_extra__,
        # so we need to inspect both the standard attributes and extras.
        extras = getattr(self, "__pydantic_extra__", {}) or {}
        all_items = {**self.__dict__, **extras}

        for key, value in all_items.items():
            if key == "datetime":
                continue
            if isinstance(value, list) and len(value) != expected_len:
                raise ValueError(
                    f"Length mismatch for column '{key}': expected {expected_len}, got {len(value)}"
                )
        return self


class BacktestTradesPayload(BaseModel):
    """Schema for items written to the backtest trades Redis queue."""

    ticker: str
    strategy_name: str
    backtest_id: str | None = None
    hash_id: str | None = None
    strategy_params: dict[str, Any] | None = None
    data: BacktestTimeSeriesData
    database: str | None = None

    @field_validator("ticker", "strategy_name")
    @classmethod
    def non_empty_string(cls, value: str) -> str:
        """Validate that ticker and strategy_name are non-empty strings.

        Args:
            value: String value to validate.

        Returns:
            Validated non-empty string.

        Raises:
            ValueError: If value is not a string or is empty/whitespace.
        """
        if not isinstance(value, str) or not value.strip():
            raise ValueError("ticker and strategy_name must be non-empty strings")
        return value

    @field_validator("strategy_params")
    @classmethod
    def validate_strategy_params(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        """Ensure strategy parameter keys are non-empty strings.

        The actual mapping from strategy parameters to Influx tag names is
        handled in the queue processor; here we only enforce a minimal contract.
        """
        if value is None:
            return value

        cleaned: dict[str, Any] = {}
        for raw_key, raw_val in value.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                raise ValueError("strategy parameter keys must be non-empty strings")
            cleaned[raw_key] = raw_val
        return cleaned


class BacktestMetricsPayload(BaseModel):
    """Schema for items written to the backtest metrics Redis queue."""

    ticker: str
    strategy_name: str
    backtest_id: str | None = None
    hash_id: str | None = None
    data: BacktestTimeSeriesData
    database: str | None = None

    @field_validator("ticker", "strategy_name")
    @classmethod
    def non_empty_string(cls, value: str) -> str:
        """Validate that ticker and strategy_name are non-empty strings.

        Args:
            value: String value to validate.

        Returns:
            Validated non-empty string.

        Raises:
            ValueError: If value is not a string or is empty/whitespace.
        """
        if not isinstance(value, str) or not value.strip():
            raise ValueError("ticker and strategy_name must be non-empty strings")
        return value


class BacktestStudiesPayload(BaseModel):
    """Schema for items written to the backtest studies Redis queue."""

    ticker: str
    strategy_name: str
    backtest_id: str | None = None
    hash_id: str | None = None
    strategy_params: dict[str, Any] | None = None
    data: BacktestTimeSeriesData
    database: str | None = None

    @field_validator("ticker", "strategy_name")
    @classmethod
    def non_empty_string(cls, value: str) -> str:
        """Validate that ticker and strategy_name are non-empty strings.

        Args:
            value: String value to validate.

        Returns:
            Validated non-empty string.

        Raises:
            ValueError: If value is not a string or is empty/whitespace.
        """
        if not isinstance(value, str) or not value.strip():
            raise ValueError("ticker and strategy_name must be non-empty strings")
        return value

    @field_validator("strategy_params")
    @classmethod
    def validate_strategy_params(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        """Ensure strategy parameter keys are non-empty strings.

        The actual mapping from strategy parameters to Influx tag names is
        handled in the queue processor; here we only enforce a minimal contract.
        """
        if value is None:
            return value

        cleaned: dict[str, Any] = {}
        for raw_key, raw_val in value.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                raise ValueError("strategy parameter keys must be non-empty strings")
            cleaned[raw_key] = raw_val
        return cleaned


__all__ = [
    "BacktestMetricsPayload",
    "BacktestStudiesPayload",
    "BacktestTimeSeriesData",
    "BacktestTradesPayload",
    "ValidationError",
]
