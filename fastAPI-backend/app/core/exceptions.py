"""
Custom exceptions for the application
"""

from typing import Any

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception."""
    
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An unexpected error occurred",
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundException(AppException):
    """Resource not found exception."""
    
    def __init__(self, resource: str = "Resource", identifier: Any = None):
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} with identifier '{identifier}' not found"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ValidationException(AppException):
    """Validation error exception."""
    
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class DuplicateException(AppException):
    """Duplicate resource exception."""
    
    def __init__(self, resource: str = "Resource", field: str = "identifier"):
        detail = f"{resource} with this {field} already exists"
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UnauthorizedException(AppException):
    """Unauthorized access exception."""
    
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(AppException):
    """Forbidden access exception."""
    
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class TenantNotFoundException(NotFoundException):
    """Tenant not found exception."""
    
    def __init__(self, identifier: Any = None):
        super().__init__(resource="Tenant", identifier=identifier)


class UserNotFoundException(NotFoundException):
    """User not found exception."""
    
    def __init__(self, identifier: Any = None):
        super().__init__(resource="User", identifier=identifier)