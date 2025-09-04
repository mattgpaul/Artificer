import os
import redis
import json
from typing import Optional, Dict, Any
from abc import abstractmethod
from infrastructure.logging.logger import get_logger
from infrastructure.client import Client

class BaseRedisClient(Client):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.namespace = self._get_namespace()

        # defaults
        self.host = "localhost"
        self.port = 6379
        self.db = 0

        self._create_connection_pool()

    @abstractmethod
    def _get_namespace(self) -> str:
        """
        Inheriting class needs to define their db namespace
        """
        pass

    def _create_connection_pool(self):
        """Create Redis connection pool with standard settings"""
        try:
            self.pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                max_connections=10,
                socket_timeout=30,
                connection_timeout=30
            )
            self.client = redis.Redis(connection_pool=self.pool)
            self.logger.info(f"Redis connection pool created for namespace {self.namespace}")
        except Exception as e:
            self.logger.error(f"Failed to create Redis connection pool {e}")
            raise

    def _build_key(self, key: str) -> str:
        """Build namsepace key: namespace:key"""
        return f"{self.namespace}:{key}"

    def get(self, key: str) -> Optional[str]:
        """
        Get string value from Redis.
        
        Arguments:
            key: The key to retrieve (will be namespaced automatically)
            
        Returns:
            String value if key exists, None if key doesn't exist or error occurs
        """
        try:
            namespaced_key = self._build_key(key)
            value = self.client.get(namespaced_key)
            self.logger.debug(f"GET {namespaced_key} -> {value}")
            return value.decode('utf-8') if value else None
        except Exception as e:
            self.logger.error(f"Error getting '{key}': {e}")
            return None

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
            """
            Set string value in Redis with optional TTL.
            
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
        
    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get JSON object from Redis and automatically parse it.
        
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

    def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set JSON object in Redis (automatically converts to string).
        
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
        """
        Test Redis connection.
        
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
