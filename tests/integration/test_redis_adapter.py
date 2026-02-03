"""
Integration tests for the Redis Cache Adapter.

These tests use fakeredis to mock Redis operations and verify:
1. Cache get/set operations
2. TTL (expiration) handling
3. Key existence checks
4. Delete operations
5. Connection pool singleton behavior
"""

import fakeredis.aioredis
import pytest
import pytest_asyncio

from adapters.redis import RedisClient


class TestRedisClientGetSet:
    """Test suite for RedisClient get/set operations."""

    @pytest_asyncio.fixture
    async def fake_redis(self) -> fakeredis.aioredis.FakeRedis:
        """Creates a fake Redis instance for testing."""
        return fakeredis.aioredis.FakeRedis(decode_responses=True)

    @pytest_asyncio.fixture
    async def client(self, fake_redis: fakeredis.aioredis.FakeRedis) -> RedisClient:
        """Creates a RedisClient with injected fake Redis."""
        return RedisClient(redis=fake_redis)

    @pytest.mark.asyncio
    async def test_set_and_get_value(self, client: RedisClient) -> None:
        """Should store and retrieve a value correctly."""
        await client.set("test_key", "test_value")

        result = await client.get("test_key")

        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key_returns_none(self, client: RedisClient) -> None:
        """Should return None when key does not exist."""
        result = await client.get("nonexistent_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_ttl(
        self, client: RedisClient, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Should set TTL when provided."""
        await client.set("expiring_key", "value", ttl_seconds=60)

        ttl = await fake_redis.ttl("expiring_key")

        # TTL should be set (between 1 and 60 seconds)
        assert 0 < ttl <= 60

    @pytest.mark.asyncio
    async def test_set_without_ttl_has_no_expiration(
        self, client: RedisClient, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Should not set TTL when not provided."""
        await client.set("persistent_key", "value")

        ttl = await fake_redis.ttl("persistent_key")

        # TTL of -1 means no expiration is set
        assert ttl == -1


class TestRedisClientExists:
    """Test suite for RedisClient exists method."""

    @pytest_asyncio.fixture
    async def fake_redis(self) -> fakeredis.aioredis.FakeRedis:
        """Creates a fake Redis instance for testing."""
        return fakeredis.aioredis.FakeRedis(decode_responses=True)

    @pytest_asyncio.fixture
    async def client(self, fake_redis: fakeredis.aioredis.FakeRedis) -> RedisClient:
        """Creates a RedisClient with injected fake Redis."""
        return RedisClient(redis=fake_redis)

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_existing_key(
        self, client: RedisClient
    ) -> None:
        """Should return True when key exists."""
        await client.set("existing_key", "value")

        result = await client.exists("existing_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_nonexistent_key(
        self, client: RedisClient
    ) -> None:
        """Should return False when key does not exist."""
        result = await client.exists("nonexistent_key")

        assert result is False


class TestRedisClientDelete:
    """Test suite for RedisClient delete method."""

    @pytest_asyncio.fixture
    async def fake_redis(self) -> fakeredis.aioredis.FakeRedis:
        """Creates a fake Redis instance for testing."""
        return fakeredis.aioredis.FakeRedis(decode_responses=True)

    @pytest_asyncio.fixture
    async def client(self, fake_redis: fakeredis.aioredis.FakeRedis) -> RedisClient:
        """Creates a RedisClient with injected fake Redis."""
        return RedisClient(redis=fake_redis)

    @pytest.mark.asyncio
    async def test_delete_removes_existing_key(self, client: RedisClient) -> None:
        """Should delete an existing key."""
        await client.set("to_delete", "value")

        await client.delete("to_delete")

        result = await client.exists("to_delete")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key_does_not_raise(
        self, client: RedisClient
    ) -> None:
        """Should not raise when deleting nonexistent key."""
        # Should not raise any exception
        await client.delete("nonexistent_key")


class TestRedisClientJsonSerialization:
    """Test suite for RedisClient JSON serialization/deserialization."""

    @pytest_asyncio.fixture
    async def fake_redis(self) -> fakeredis.aioredis.FakeRedis:
        """Creates a fake Redis instance for testing."""
        return fakeredis.aioredis.FakeRedis(decode_responses=True)

    @pytest_asyncio.fixture
    async def client(self, fake_redis: fakeredis.aioredis.FakeRedis) -> RedisClient:
        """Creates a RedisClient with injected fake Redis."""
        return RedisClient(redis=fake_redis)

    @pytest.mark.asyncio
    async def test_set_and_get_dict(self, client: RedisClient) -> None:
        """Should serialize and deserialize a dictionary correctly."""
        data = {"name": "Luke Skywalker", "height": "172", "mass": "77"}

        await client.set("person:1", data)
        result = await client.get("person:1")

        assert result == data
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_set_and_get_complex_swapi_response(
        self, client: RedisClient
    ) -> None:
        """Should handle complex SWAPI-like responses with nested structures."""
        swapi_person = {
            "name": "Luke Skywalker",
            "height": "172",
            "mass": "77",
            "hair_color": "blond",
            "skin_color": "fair",
            "eye_color": "blue",
            "birth_year": "19BBY",
            "gender": "male",
            "homeworld": "https://swapi.dev/api/planets/1/",
            "films": [
                "https://swapi.dev/api/films/1/",
                "https://swapi.dev/api/films/2/",
                "https://swapi.dev/api/films/3/",
            ],
            "species": [],
            "vehicles": [
                "https://swapi.dev/api/vehicles/14/",
                "https://swapi.dev/api/vehicles/30/",
            ],
            "starships": [
                "https://swapi.dev/api/starships/12/",
                "https://swapi.dev/api/starships/22/",
            ],
            "created": "2014-12-09T13:50:51.644000Z",
            "edited": "2014-12-20T21:17:56.891000Z",
            "url": "https://swapi.dev/api/people/1/",
        }

        await client.set("swapi:people:1", swapi_person, ttl_seconds=300)
        result = await client.get("swapi:people:1")

        assert result == swapi_person
        assert result["name"] == "Luke Skywalker"
        assert len(result["films"]) == 3
        assert result["films"][0] == "https://swapi.dev/api/films/1/"

    @pytest.mark.asyncio
    async def test_set_and_get_list(self, client: RedisClient) -> None:
        """Should serialize and deserialize a list correctly."""
        data = [1, 2, 3, "four", {"five": 5}]

        await client.set("list_key", data)
        result = await client.get("list_key")

        assert result == data
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_set_and_get_nested_structure(self, client: RedisClient) -> None:
        """Should handle deeply nested structures."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep",
                        "numbers": [1, 2, 3],
                    }
                }
            }
        }

        await client.set("nested", data)
        result = await client.get("nested")

        assert result == data
        assert result["level1"]["level2"]["level3"]["value"] == "deep"

    @pytest.mark.asyncio
    async def test_set_and_get_with_none_values(self, client: RedisClient) -> None:
        """Should handle dictionaries with None values."""
        data = {"name": "Test", "optional_field": None}

        await client.set("with_none", data)
        result = await client.get("with_none")

        assert result == data
        assert result["optional_field"] is None

    @pytest.mark.asyncio
    async def test_set_and_get_boolean_values(self, client: RedisClient) -> None:
        """Should preserve boolean types after serialization."""
        data = {"active": True, "deleted": False}

        await client.set("booleans", data)
        result = await client.get("booleans")

        assert result["active"] is True
        assert result["deleted"] is False


class TestRedisClientConnectionPool:
    """Test suite for RedisClient connection pool singleton behavior."""

    @pytest.mark.asyncio
    async def test_default_client_uses_singleton_pool(self) -> None:
        """Multiple clients without injected redis should share the same pool."""
        # This tests the factory method behavior
        # In production, get_redis_client() should return singleton
        from adapters.redis import get_redis_client

        client1 = get_redis_client()
        client2 = get_redis_client()

        # Both should reference the same underlying connection
        assert client1 is client2
