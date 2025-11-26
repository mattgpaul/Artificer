import pickle
import zlib
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from infrastructure.logging.logger import get_logger
from infrastructure.redis.redis import BaseRedisClient

_config_cache: tuple[int, int] | None = None
_logger_config = get_logger("OhlcvCacheConfig")


def _get_cache_config() -> tuple[int, int]:
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config_path = Path(__file__).parent / "ohlcv_cache_config.yaml"
    if not config_path.exists():
        _logger_config.warning(
            f"OHLCV cache config not found at {config_path}, using defaults"
        )
        _config_cache = (1000000000, 3600)
        return _config_cache

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        max_bytes = int(config.get("max_cache_bytes", 1000000000))
        ttl_seconds = int(config.get("ttl_seconds", 3600))
        _config_cache = (max_bytes, ttl_seconds)
        _logger_config.debug(
            f"Loaded OHLCV cache config: max_bytes={max_bytes}, ttl_seconds={ttl_seconds}"
        )
        return _config_cache
    except Exception as e:
        _logger_config.warning(f"Error loading OHLCV cache config: {e}, using defaults")
        _config_cache = (1000000000, 3600)
        return _config_cache


class OhlcvCacheClient(BaseRedisClient):
    def _get_namespace(self) -> str:
        return "ohlcv_cache"

    def get_usage_key(self) -> str:
        return "usage:total_bytes"

    def get_size_key(self, hash_id: str, ticker: str) -> str:
        return f"size:{hash_id}:{ticker}"

    def get_current_usage(self) -> int:
        usage_str = self.get(self.get_usage_key())
        if usage_str:
            try:
                return int(usage_str)
            except (ValueError, TypeError):
                return 0
        return 0

    def update_usage(self, delta_bytes: int, ttl: int) -> None:
        current = self.get_current_usage()
        new_total = max(0, current + delta_bytes)
        self.set(self.get_usage_key(), str(new_total), ttl=ttl)

    def record_size(self, hash_id: str, ticker: str, size_bytes: int, ttl: int) -> None:
        size_key = self.get_size_key(hash_id, ticker)
        self.set(size_key, str(size_bytes), ttl=ttl)

    def get_recorded_size(self, hash_id: str, ticker: str) -> int:
        size_key = self.get_size_key(hash_id, ticker)
        size_str = self.get(size_key)
        if size_str:
            try:
                return int(size_str)
            except (ValueError, TypeError):
                return 0
        return 0

    def get_binary(self, key: str) -> bytes | None:
        try:
            namespaced_key = self._build_key(key)
            value = self.client.get(namespaced_key)
            return value if value else None
        except Exception as e:
            self.logger.error(f"Error getting binary '{key}': {e}")
            return None

    def set_binary(self, key: str, value: bytes, ttl: int | None = None) -> bool:
        try:
            namespaced_key = self._build_key(key)
            result = self.client.set(namespaced_key, value, ex=ttl)
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error setting binary '{key}': {e}")
            return False


def _serialize_dataframe(df: pd.DataFrame) -> bytes:
    pickled = pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL)
    compressed = zlib.compress(pickled, level=6)
    return compressed


def _deserialize_dataframe(data: bytes) -> pd.DataFrame:
    decompressed = zlib.decompress(data)
    df = pickle.loads(decompressed)
    return df


def make_key(hash_id: str, ticker: str) -> str:
    return f"{hash_id}:{ticker}"


_client: OhlcvCacheClient | None = None
_logger = get_logger("OhlcvCache")


def _get_client() -> OhlcvCacheClient:
    global _client
    if _client is None:
        _client = OhlcvCacheClient()
    return _client


def store_ohlcv_frame(hash_id: str, ticker: str, df: pd.DataFrame) -> None:
    if df is None or df.empty:
        return

    max_bytes, ttl_seconds = _get_cache_config()
    client = _get_client()

    try:
        serialized = _serialize_dataframe(df)
        size_bytes = len(serialized)

        current_usage = client.get_current_usage()
        if current_usage + size_bytes > max_bytes:
            _logger.warning(
                f"OHLCV cache full: {current_usage + size_bytes} > {max_bytes}. "
                f"Skipping cache for {hash_id}:{ticker}"
            )
            return

        key = make_key(hash_id, ticker)
        success = client.set_binary(key, serialized, ttl=ttl_seconds)
        if success:
            client.record_size(hash_id, ticker, size_bytes, ttl_seconds)
            client.update_usage(size_bytes, ttl_seconds)
            _logger.debug(f"Cached OHLCV for {hash_id}:{ticker} ({size_bytes} bytes)")
        else:
            _logger.warning(f"Failed to cache OHLCV for {hash_id}:{ticker}")
    except Exception as e:
        _logger.warning(f"Error caching OHLCV for {hash_id}:{ticker}: {e}")


def load_ohlcv_frame(hash_id: str, ticker: str) -> pd.DataFrame | None:
    client = _get_client()
    key = make_key(hash_id, ticker)

    try:
        data = client.get_binary(key)
        if data is None:
            return None

        df = _deserialize_dataframe(data)
        _logger.debug(f"Loaded OHLCV from cache for {hash_id}:{ticker}")
        return df
    except Exception as e:
        _logger.warning(f"Error loading OHLCV from cache for {hash_id}:{ticker}: {e}")
        return None


def clear_for_hash(hash_id: str) -> None:
    client = _get_client()
    data_pattern = f"{hash_id}:*"
    size_pattern = f"size:{hash_id}:*"
    data_keys = client.keys(data_pattern)
    size_keys = client.keys(size_pattern)

    if not data_keys and not size_keys:
        return

    total_freed = 0
    for key in data_keys:
        parts = key.split(":", 1)
        if len(parts) == 2:
            ticker = parts[1]
            size_bytes = client.get_recorded_size(hash_id, ticker)
            if size_bytes > 0:
                total_freed += size_bytes
        client.delete(key)

    for key in size_keys:
        client.delete(key)

    if total_freed > 0:
        max_bytes, ttl_seconds = _get_cache_config()
        client.update_usage(-total_freed, ttl_seconds)

    cleared_count = len(data_keys) + len(size_keys)
    _logger.info(f"Cleared {cleared_count} cached OHLCV entries for hash {hash_id}")

