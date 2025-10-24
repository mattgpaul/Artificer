"""Redis client base class with namespacing and TTL support.

This module provides the BaseRedisClient abstract class for Redis operations
with automatic key namespacing, TTL management, and support for various data
types including strings, hashes, JSON, and sets.
"""

import json
import os
from abc import abstractmethod
from typing import Any

import redis

from infrastructure.client import Client
from infrastructure.logging.logger import get_logger


class BaseRedisClient(Client):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.namespace = self._get_namespace()

        # Configuration from environment variables with fallback defaults
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.db = int(os.getenv("REDIS_DB", "0"))
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
        self.socket_timeout = int(os.getenv("REDIS_SOCKET_TIMEOUT", "30"))

        self._create_connection_pool()

    @abstractmethod
    def _get_namespace(self) -> str:
        """Inheriting class needs to define their db namespace"""
        pass

    def _create_connection_pool(self):
        """Create Redis connection pool with configurable settings"""
        try:
            self.pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
            )
            self.client = redis.Redis(connection_pool=self.pool)
            self.logger.info(
                f"Redis connection pool created for namespace: {self.namespace} (host: {self.host}, port: {self.port}, db: {self.db})"
            )
        except Exception as e:
            self.logger.error(f"Failed to create Redis connection pool {e}")
            raise

    def _build_key(self, key: str) -> str:
        """Build namsepace key: namespace:key"""
        return f"{self.namespace}:{key}"

    def get(self, key: str) -> str | None:
        """Get string value from Redis.

        Arguments:
            key: The key to retrieve (will be namespaced automatically)

        Returns:
            String value if key exists, None if key doesn't exist or error occurs
        """
        try:
            namespaced_key = self._build_key(key)
            value = self.client.get(namespaced_key)
            self.logger.debug(f"GET {namespaced_key} -> {value}")
            return value.decode("utf-8") if value else None
        except Exception as e:
            self.logger.error(f"Error getting '{key}': {e}")
            return None

    def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """Set string value in Redis with optional TTL.

        Arguments:
            key: The key to set (will be namespaced automatically)
            value: The string value to store
            ttl: Time to live in seconds (optional)

        Returns:
            True if successful, False if error occurs
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.set(namespaced_key, value, ex=ttl)
            self.logger.debug(f"SET {namespaced_key} = {value} (ttl: {ttl}) -> {result}")
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error setting '{key}: {e}")
            return False

    def hget(self, key: str, field: str) -> str | None:
        """Get a field value from a Redis hash.

        Arguments:
            key: The hash key (will be namespaced automatically)
            field: The field name within the hash

        Returns:
            String value if field exists, None otherwise
        """
        try:
            namespaced_key = self._build_key(key)
            value = self.client.hget(namespaced_key, field)
            self.logger.debug(f"HGET {namespaced_key} {field} -> {value}")
            return value.decode("utf-8") if value else None
        except Exception as e:
            self.logger.error(f"Error getting hash field '{key}.{field}': {e}")
            return None

    def hset(self, key: str, field: str, value: str, ttl: int | None = None) -> bool:
        """Set a field value in a Redis hash with optional TTL.

        Arguments:
            key: The hash key (will be namespaced automatically)
            field: The field name within the hash
            value: The value to store
            ttl: Time to live in seconds (optional)

        Returns:
            True if successful, False if error occurs
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.hset(namespaced_key, field, value)

            # Set TTL if provided
            if ttl is not None:
                self.client.expire(namespaced_key, ttl)

            self.logger.debug(f"HSET {namespaced_key} {field} = {value} (ttl: {ttl}) -> {result}")
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error setting hash field '{key}.{field}': {e}")
            return False

    def hgetall(
        self,
        key: str,
    ) -> dict[str, str]:
        """Get all field-value pairs from a Redis hash.

        Arguments:
            key: The hash key (will be namespaced automatically)

        Returns:
            Dictionary of field-value pairs, empty dict if key doesn't exist
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.hgetall(namespaced_key)
            decoded_result = {k.decode("utf-8"): v.decode("utf-8") for k, v in result.items()}
            self.logger.debug(f"HGETALL {namespaced_key} -> {len(decoded_result)} fields")
            return decoded_result
        except Exception as e:
            self.logger.error(f"Error getting all hash fields '{key}': {e}")
            return {}

    def hmset(self, key: str, mapping: dict[str, Any], ttl: int | None = None) -> bool:
        """Set multiple field-value pairs in a Redis hash with optional TTL.

        Arguments:
            key: The hash key (will be namespaced automatically)
            mapping: Dictionary of field-value pairs to set
            ttl: Time to live in seconds (optional)

        Returns:
            True if successful, False if error occurs
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.hmset(namespaced_key, mapping)

            # Set TTL if provided
            if ttl is not None:
                self.client.expire(namespaced_key, ttl)

            self.logger.debug(f"HMSET {namespaced_key} -> {len(mapping)} fields set (ttl: {ttl})")
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error setting hash fields '{key}': {e}")
            return False

    def hdel(self, key: str, *fields: str) -> int:
        """Delete one or more fields from a Redis hash.

        Arguments:
            key: The hash key (will be namespaced automatically)
            fields: Field names to delete

        Returns:
            Number of fields that were removed
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.hdel(namespaced_key, *fields)
            self.logger.debug(f"HDEL {namespaced_key} {fields} -> {result} deleted")
            return result
        except Exception as e:
            self.logger.error(f"Error deleting hash fields '{key}.{fields}': {e}")
            return 0

    def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        """Get JSON object from Redis and automatically parse it.

        Arguments:
            key: The key to retrieve (will be namespaced automatically)

        Returns:
            Dictionary if key exists and contains valid JSON, None otherwise
        """
        try:
            json_str = self.get(key)  # This will handle debug logging
            if json_str:
                result = json.loads(json_str)
                self.logger.debug(f"JSON parsed for {key}: {len(str(result))} chars")
                return result
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON for key '{key}': {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting JSON key '{key}': {e}")
            return None

    def set_json(self, key: str, value: dict[str, Any] | list[Any], ttl: int | None = None) -> bool:
        """Set JSON object in Redis (automatically converts to string).

        Arguments:
            key: The key to set (will be namespaced automatically)
            value: Dictionary to store as JSON
            ttl: Time to live in seconds (optional)

        Returns:
            True if successful, False if error occurs
        """
        try:
            json_str = json.dumps(value)
            self.logger.debug(f"JSON serialized for {key}: {len(json_str)} chars")
            return self.set(key, json_str, ttl)  # This will handle SET debug logging
        except Exception as e:
            self.logger.error(f"Error setting JSON key '{key}': {e}")
            return False

    def ping(self) -> bool:
        """Test Redis connection.

        Returns:
            True if Redis is responding, False if connection failed
        """
        try:
            result = self.client.ping()
            self.logger.debug(f"PING -> {result}")
            return result
        except Exception as e:
            self.logger.error(f"Redis ping failed: {e}")
            return False

    def sadd(self, key: str, *members: str, ttl: int | None = None) -> int:
        """Add one or more members to a Redis set with optional TTL.

        Arguments:
            key: The set key (will be namespaced automatically)
            members: One or more values to add to the set
            ttl: Time to live in seconds (optional)

        Returns:
            Number of members that were added (excludes duplicates)
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.sadd(namespaced_key, *members)

            # Set TTL if provided
            if ttl is not None:
                self.client.expire(namespaced_key, ttl)

            self.logger.debug(f"SADD {namespaced_key} {members} -> {result} added (ttl: {ttl})")
            return result
        except Exception as e:
            self.logger.error(f"Error adding to set '{key}': {e}")
            return 0

    def smembers(self, key: str) -> set:
        """Get all members of a Redis set.

        Arguments:
            key: The set key (will be namespaced automatically)

        Returns:
            Set of all members, empty set if key doesn't exist
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.smembers(namespaced_key)
            decoded_result = {member.decode("utf-8") for member in result}
            self.logger.debug(f"SMEMBERS {namespaced_key} -> {len(decoded_result)} members")
            return decoded_result
        except Exception as e:
            self.logger.error(f"Error getting set members '{key}': {e}")
            return set()

    def srem(self, key: str, *members: str) -> int:
        """Remove one or more members from a Redis set.

        Arguments:
            key: The set key (will be namespaced automatically)
            members: One or more values to remove from the set

        Returns:
            Number of members that were removed
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.srem(namespaced_key, *members)
            self.logger.debug(f"SREM {namespaced_key} {members} -> {result} removed")
            return result
        except Exception as e:
            self.logger.error(f"Error removing from set '{key}': {e}")
            return 0

    def sismember(self, key: str, member: str) -> bool:
        """Check if a member exists in a Redis set.

        Arguments:
            key: The set key (will be namespaced automatically)
            member: The value to check for membership

        Returns:
            True if member exists in set, False otherwise
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.sismember(namespaced_key, member)
            self.logger.debug(f"SISMEMBER {namespaced_key} {member} -> {result}")
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error checking set membership '{key}.{member}': {e}")
            return False

    def scard(self, key: str) -> int:
        """Get the number of members in a Redis set.

        Arguments:
            key: The set key (will be namespaced automatically)

        Returns:
            Number of members in the set, 0 if key doesn't exist
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.scard(namespaced_key)
            self.logger.debug(f"SCARD {namespaced_key} -> {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error getting set cardinality '{key}': {e}")
            return 0

    def lpush(self, key: str, *values: str, ttl: int | None = None) -> int:
        """Push one or more values to the left (front) of a Redis list with optional TTL.

        Arguments:
            key: The list key (will be namespaced automatically)
            values: One or more values to push to the front
            ttl: Time to live in seconds (optional)

        Returns:
            Length of the list after the push operations
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.lpush(namespaced_key, *values)

            # Set TTL if provided
            if ttl is not None:
                self.client.expire(namespaced_key, ttl)

            self.logger.debug(
                f"LPUSH {namespaced_key} {values} -> list length: {result} (ttl: {ttl})"
            )
            return result
        except Exception as e:
            self.logger.error(f"Error pushing to front of list '{key}': {e}")
            return 0

    def rpush(self, key: str, *values: str, ttl: int | None = None) -> int:
        """Push one or more values to the right (back) of a Redis list with optional TTL.

        Arguments:
            key: The list key (will be namespaced automatically)
            values: One or more values to push to the back
            ttl: Time to live in seconds (optional)

        Returns:
            Length of the list after the push operations
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.rpush(namespaced_key, *values)

            # Set TTL if provided
            if ttl is not None:
                self.client.expire(namespaced_key, ttl)

            self.logger.debug(
                f"RPUSH {namespaced_key} {values} -> list length: {result} (ttl: {ttl})"
            )
            return result
        except Exception as e:
            self.logger.error(f"Error pushing to back of list '{key}': {e}")
            return 0

    def lpop(self, key: str) -> str | None:
        """Pop and return a value from the left (front) of a Redis list.

        Arguments:
            key: The list key (will be namespaced automatically)

        Returns:
            The popped value if list exists and has elements, None otherwise
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.lpop(namespaced_key)
            value = result.decode("utf-8") if result else None
            self.logger.debug(f"LPOP {namespaced_key} -> {value}")
            return value
        except Exception as e:
            self.logger.error(f"Error popping from front of list '{key}': {e}")
            return None

    def rpop(self, key: str) -> str | None:
        """Pop and return a value from the right (back) of a Redis list.

        Arguments:
            key: The list key (will be namespaced automatically)

        Returns:
            The popped value if list exists and has elements, None otherwise
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.rpop(namespaced_key)
            value = result.decode("utf-8") if result else None
            self.logger.debug(f"RPOP {namespaced_key} -> {value}")
            return value
        except Exception as e:
            self.logger.error(f"Error popping from back of list '{key}': {e}")
            return None

    def llen(self, key: str) -> int:
        """Get the length of a Redis list.

        Arguments:
            key: The list key (will be namespaced automatically)

        Returns:
            Length of the list, 0 if key doesn't exist
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.llen(namespaced_key)
            self.logger.debug(f"LLEN {namespaced_key} -> {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error getting list length '{key}': {e}")
            return 0

    def lrange(self, key: str, start: int, end: int) -> list:
        """Get a range of elements from a Redis list.

        Arguments:
            key: The list key (will be namespaced automatically)
            start: Start index (0-based, can be negative)
            end: End index (inclusive, -1 means last element)

        Returns:
            List of elements in the specified range, empty list if key doesn't exist
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.lrange(namespaced_key, start, end)
            decoded_result = [item.decode("utf-8") for item in result]
            self.logger.debug(
                f"LRANGE {namespaced_key} [{start}:{end}] -> {len(decoded_result)} items"
            )
            return decoded_result
        except Exception as e:
            self.logger.error(f"Error getting list range '{key}[{start}:{end}]': {e}")
            return []

    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis.

        Arguments:
            key: The key to check (will be namespaced automatically)

        Returns:
            True if key exists, False otherwise
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.exists(namespaced_key)
            self.logger.debug(f"EXISTS {namespaced_key} -> {bool(result)}")
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error checking existence of key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a key from Redis.

        Arguments:
            key: The key to delete (will be namespaced automatically)

        Returns:
            True if key was deleted, False if key didn't exist or error occurred
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.delete(namespaced_key)
            self.logger.debug(f"DELETE {namespaced_key} -> {result} deleted")
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error deleting key '{key}': {e}")
            return False

    def expire(self, key: str, seconds: int) -> bool:
        """Set TTL (time to live) for a key in seconds.

        Arguments:
            key: The key to set expiration for (will be namespaced automatically)
            seconds: Number of seconds until key expires

        Returns:
            True if TTL was set, False if key doesn't exist or error occurred
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.expire(namespaced_key, seconds)
            self.logger.debug(f"EXPIRE {namespaced_key} {seconds}s -> {bool(result)}")
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error setting expiration for key '{key}': {e}")
            return False

    def ttl(self, key: str) -> int:
        """Get the remaining time to live for a key in seconds.

        Arguments:
            key: The key to check TTL for (will be namespaced automatically)

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        try:
            namespaced_key = self._build_key(key)
            result = self.client.ttl(namespaced_key)
            self.logger.debug(f"TTL {namespaced_key} -> {result}s")
            return result
        except Exception as e:
            self.logger.error(f"Error getting TTL for key '{key}': {e}")
            return -2

    def keys(self, pattern: str = "*") -> list:
        """Find keys matching a pattern within this namespace.

        Arguments:
            pattern: Pattern to match (wildcards allowed, applied after namespace)

        Returns:
            List of matching keys (with namespace stripped)
        """
        try:
            namespaced_pattern = self._build_key(pattern)
            result = self.client.keys(namespaced_pattern)
            # Strip namespace from results
            namespace_prefix = f"{self.namespace}:"
            stripped_keys = [key.decode("utf-8").replace(namespace_prefix, "", 1) for key in result]
            self.logger.debug(f"KEYS {namespaced_pattern} -> {len(stripped_keys)} matches")
            return stripped_keys
        except Exception as e:
            self.logger.error(f"Error finding keys with pattern '{pattern}': {e}")
            return []

    def flushdb(self) -> bool:
        """WARNING: Delete ALL keys in the current database.
        Use with extreme caution!

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.client.flushdb()
            self.logger.warning(f"FLUSHDB executed -> {bool(result)} (ALL KEYS DELETED)")
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error flushing database: {e}")
            return False

    def pipeline_execute(self, operations: list) -> bool:
        """Execute multiple operations in a pipeline.

        Arguments:
            operations: List of tuples (method_name, key, *args)

        Returns:
            True if all operations succeeded
        """
        try:
            pipeline = self.client.pipeline()

            for operation in operations:
                method_name, key, *args = operation
                namespaced_key = self._build_key(key)
                getattr(pipeline, method_name)(namespaced_key, *args)

            results = pipeline.execute()
            success = all(results)
            self.logger.debug(f"Pipeline executed {len(operations)} operations -> {success}")
            return success
        except Exception as e:
            self.logger.error(f"Error in pipeline execution: {e}")
            return False
