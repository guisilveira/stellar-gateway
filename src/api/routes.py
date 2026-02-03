"""
API Routes for SWAPI Proxy.

This module defines the FastAPI routes for the Stellar Gateway API.
Implements dynamic resource routes and the /me endpoint.
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query

from api.dependencies import GetResourceUseCaseDep, ListResourcesUseCaseDep
from core.security import CurrentUser

# Valid SWAPI resource types
VALID_RESOURCES = frozenset(
    {"people", "planets", "films", "species", "vehicles", "starships"}
)

# Sort order type
SortOrder = Literal["asc", "desc"]

# Create router
router = APIRouter(tags=["SWAPI"])


@router.get("/me")
async def get_current_user_info(current_user: CurrentUser) -> dict[str, Any]:
    """
    Returns the authenticated user's information.

    This endpoint returns the decoded Firebase token claims,
    providing information about the currently authenticated user.

    Args:
        current_user: The authenticated user's decoded token.

    Returns:
        A dictionary containing the user's information.
    """
    return {
        "uid": current_user.get("uid"),
        "email": current_user.get("email"),
        "name": current_user.get("name"),
        "email_verified": current_user.get("email_verified", False),
    }


@router.get("/{resource}")
async def list_resources(
    resource: str,
    current_user: CurrentUser,
    use_case: ListResourcesUseCaseDep,
    page: Annotated[int | None, Query(ge=1, description="Page number")] = None,
    search: Annotated[
        str | None, Query(min_length=1, description="Search query")
    ] = None,
    sort_by: Annotated[
        str | None, Query(description="Field to sort by (e.g., name, height)")
    ] = None,
    sort_order: Annotated[
        SortOrder, Query(description="Sort order: asc or desc")
    ] = "asc",
) -> dict[str, Any]:
    """
    Lists resources of a given type with pagination, filtering, and sorting.

    Supports all SWAPI resource types: people, planets, films, species,
    vehicles, and starships.

    Query Parameters:
        - page: Page number for pagination (default: 1)
        - search: Search/filter query (maps to SWAPI's ?search= parameter)
        - sort_by: Field to sort results by (sorting is done in memory)
        - sort_order: Sort direction - "asc" (default) or "desc"

    Args:
        resource: The resource type (e.g., "people", "planets").
        current_user: The authenticated user (injected).
        use_case: The listing use case (injected).
        page: Optional page number.
        search: Optional search query.
        sort_by: Optional field to sort by.
        sort_order: Sort direction.

    Returns:
        A paginated response with count, next, previous, and results.

    Raises:
        HTTPException: 400 if resource type is invalid.
        HTTPException: 502 if SWAPI is unavailable.
    """
    # Resource validation is handled by exception handler
    return await use_case.execute(
        resource_type=resource,
        page=page,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{resource}/{resource_id}")
async def get_resource(
    resource: str,
    resource_id: int,
    current_user: CurrentUser,
    use_case: GetResourceUseCaseDep,
    enrich: Annotated[
        bool, Query(description="Enrich URLs with resource names")
    ] = True,
) -> dict[str, Any]:
    """
    Fetches a single resource by type and ID.

    Supports all SWAPI resource types: people, planets, films, species,
    vehicles, and starships.

    Query Parameters:
        - enrich: Whether to replace URL fields with resource names (default: true)

    Args:
        resource: The resource type (e.g., "people", "planets").
        resource_id: The unique identifier of the resource.
        current_user: The authenticated user (injected).
        use_case: The get resource use case (injected).
        enrich: Whether to enrich URL fields.

    Returns:
        The resource data (optionally enriched).

    Raises:
        HTTPException: 404 if resource not found.
        HTTPException: 502 if SWAPI is unavailable.
    """
    return await use_case.execute(
        resource_type=resource,
        resource_id=resource_id,
        enrich=enrich,
    )
