"""
Domain Exceptions.

This module defines custom exceptions for the domain layer.
These exceptions are independent of any external framework.
"""


class StellarGatewayException(Exception):
    """Base exception for all Stellar Gateway errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class ResourceNotFoundException(StellarGatewayException):
    """
    Raised when a requested resource is not found.

    Attributes:
        resource_type: The type of resource (e.g., "people", "planets").
        resource_id: The ID of the resource that was not found.
    """

    def __init__(
        self,
        resource_type: str,
        resource_id: int | str,
        message: str | None = None,
    ) -> None:
        self.resource_type = resource_type
        self.resource_id = resource_id
        default_message = f"{resource_type.capitalize()} with ID {resource_id} not found"
        super().__init__(message or default_message)


class ExternalServiceException(StellarGatewayException):
    """
    Raised when an external service (e.g., SWAPI) fails.

    Attributes:
        service_name: The name of the external service.
        status_code: The HTTP status code returned (if applicable).
    """

    def __init__(
        self,
        service_name: str,
        status_code: int | None = None,
        message: str | None = None,
    ) -> None:
        self.service_name = service_name
        self.status_code = status_code
        default_message = f"External service '{service_name}' failed"
        if status_code:
            default_message += f" with status {status_code}"
        super().__init__(message or default_message)
