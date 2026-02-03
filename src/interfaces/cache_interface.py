"""
Interfaces for caching layer.

This module defines Protocols (contracts) that cache adapters must implement.
Following the Dependency Inversion Principle (DIP).
"""

from typing import Any, Protocol


class CacheInterface(Protocol):
    """
    Contract for cache operations.

    Any adapter that provides caching (Redis, Memcached, in-memory)
    must implement this protocol.

    Values are automatically serialized/deserialized as JSON,
    allowing storage of complex Python objects (dicts, lists, etc.).
    """

    async def get(self, key: str) -> Any | None:
        """
        Retrieves a value from the cache.

        Args:
            key: The cache key to retrieve.

        Returns:
            The cached value (deserialized from JSON), or None if not found.
        """
        ...

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """
        Stores a value in the cache.

        Args:
            key: The cache key to store.
            value: The value to cache (will be serialized to JSON).
            ttl_seconds: Optional time-to-live in seconds. If None, no expiration.
        """
        ...

    async def delete(self, key: str) -> None:
        """
        Deletes a value from the cache.

        Args:
            key: The cache key to delete.
        """
        ...

    async def exists(self, key: str) -> bool:
        """
        Checks if a key exists in the cache.

        Args:
            key: The cache key to check.

        Returns:
            True if the key exists, False otherwise.
        """
        ...
