"""
Redis Cache Adapter.

This module implements the CacheInterface using redis-py for async Redis operations.
Uses a singleton connection pool for efficient connection management.
Handles JSON serialization/deserialization automatically.
"""

import json
from typing import Any

import redis.asyncio as redis

from core.config import settings


# Module-level singleton for the Redis client
_redis_client: "RedisClient | None" = None


class RedisClient:
    """
    Async Redis client implementing the CacheInterface protocol.

    Uses redis-py's async interface for non-blocking cache operations.
    Supports dependency injection of the Redis connection for testing.

    Automatically serializes values to JSON on set() and deserializes on get(),
    allowing storage of complex Python objects (dicts, lists, etc.).

    Attributes:
        _redis: The underlying Redis connection instance.
    """

    def __init__(
        self,
        redis: Any | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        """
        Initializes the Redis client.

        Args:
            redis: Optional pre-configured Redis instance (for testing).
            host: Redis host (defaults to settings.REDIS_HOST).
            port: Redis port (defaults to settings.REDIS_PORT).
        """
        if redis is not None:
            self._redis = redis
        else:
            self._redis = self._create_connection(
                host=host or settings.REDIS_HOST,
                port=port or settings.REDIS_PORT,
            )

    def _create_connection(self, host: str, port: int) -> redis.Redis:
        """
        Creates a Redis connection with connection pooling.

        Args:
            host: Redis server hostname.
            port: Redis server port.

        Returns:
            A configured async Redis client instance.
        """
        return redis.Redis(
            host=host,
            port=port,
            decode_responses=True,  # Return strings instead of bytes
        )

    async def get(self, key: str) -> Any | None:
        """
        Retrieves a value from the cache and deserializes it from JSON.

        Args:
            key: The cache key to retrieve.

        Returns:
            The cached value (deserialized from JSON), or None if not found.
        """
        result = await self._redis.get(key)

        if result is None:
            return None

        return json.loads(result)

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """
        Serializes a value to JSON and stores it in the cache.

        Args:
            key: The cache key to store.
            value: The value to cache (will be serialized to JSON).
            ttl_seconds: Optional time-to-live in seconds. If None, no expiration.
        """
        serialized = json.dumps(value)

        if ttl_seconds is not None:
            await self._redis.set(key, serialized, ex=ttl_seconds)
        else:
            await self._redis.set(key, serialized)

    async def delete(self, key: str) -> None:
        """
        Deletes a value from the cache.

        Args:
            key: The cache key to delete.
        """
        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        """
        Checks if a key exists in the cache.

        Args:
            key: The cache key to check.

        Returns:
            True if the key exists, False otherwise.
        """
        return await self._redis.exists(key) > 0

    async def close(self) -> None:
        """
        Closes the Redis connection.

        Should be called during application shutdown.
        """
        await self._redis.aclose()


def get_redis_client() -> RedisClient:
    """
    Returns a singleton RedisClient instance.

    This ensures all parts of the application share the same
    connection pool for efficient resource usage.

    Returns:
        The singleton RedisClient instance.
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = RedisClient()

    return _redis_client
