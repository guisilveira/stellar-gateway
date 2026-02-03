"""
Dependency Injection for FastAPI.

This module provides dependency providers for use cases and adapters.
Following the Dependency Inversion Principle (DIP).
"""

from typing import Annotated

from fastapi import Depends

from adapters.redis import get_redis_client
from adapters.swapi import get_swapi_client
from interfaces.cache_interface import CacheInterface
from interfaces.swapi_interface import SwapiInterface
from use_cases.get_resource import GetResourceUseCase
from use_cases.list_resources import ListResourcesUseCase


def get_swapi() -> SwapiInterface:
    """
    Provides the SWAPI client singleton.

    Returns:
        The SWAPI client instance.
    """
    return get_swapi_client()


def get_cache() -> CacheInterface:
    """
    Provides the Redis cache client singleton.

    Returns:
        The Redis cache client instance.
    """
    return get_redis_client()


def get_get_resource_use_case(
    swapi: Annotated[SwapiInterface, Depends(get_swapi)],
    cache: Annotated[CacheInterface, Depends(get_cache)],
) -> GetResourceUseCase:
    """
    Provides the GetResourceUseCase with injected dependencies.

    Args:
        swapi: The SWAPI client.
        cache: The cache client.

    Returns:
        A configured GetResourceUseCase instance.
    """
    return GetResourceUseCase(swapi=swapi, cache=cache)


def get_list_resources_use_case(
    swapi: Annotated[SwapiInterface, Depends(get_swapi)],
    cache: Annotated[CacheInterface, Depends(get_cache)],
) -> ListResourcesUseCase:
    """
    Provides the ListResourcesUseCase with injected dependencies.

    Args:
        swapi: The SWAPI client.
        cache: The cache client.

    Returns:
        A configured ListResourcesUseCase instance.
    """
    return ListResourcesUseCase(swapi=swapi, cache=cache)


# Type aliases for dependency injection
GetResourceUseCaseDep = Annotated[
    GetResourceUseCase, Depends(get_get_resource_use_case)
]
ListResourcesUseCaseDep = Annotated[
    ListResourcesUseCase, Depends(get_list_resources_use_case)
]
