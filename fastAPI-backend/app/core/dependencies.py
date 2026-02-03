"""
FastAPI dependencies for dependency injection
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.core.exceptions import UnauthorizedException, TenantNotFoundException
from app.core.security import decode_access_token


# Type alias for database session dependency
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_db() -> AsyncSession:
    """Get database session dependency."""
    async for session in get_db_session():
        yield session


async def get_current_tenant(
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
    tenant_id: Annotated[str | None, Query(alias="tenantId")] = None,
) -> UUID | None:
    """
    Extract current tenant from request headers or query params.
    Used for tenant-scoped operations.
    """
    tenant = x_tenant_id or tenant_id
    
    if tenant:
        try:
            return UUID(tenant)
        except ValueError:
            raise TenantNotFoundException(identifier=tenant)
    
    return None


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> UUID | None:
    """Extract current user ID from JWT token."""
    if not authorization:
        return None
    
    if not authorization.startswith("Bearer "):
        raise UnauthorizedException(detail="Invalid authorization header format")
    
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    
    if not payload:
        raise UnauthorizedException(detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if user_id:
        try:
            return UUID(user_id)
        except ValueError:
            raise UnauthorizedException(detail="Invalid user identifier in token")
    
    return None


def require_tenant(
    tenant_id: Annotated[UUID | None, Depends(get_current_tenant)]
) -> UUID:
    """Require tenant ID to be present."""
    if not tenant_id:
        raise TenantNotFoundException(
            identifier="missing - X-Tenant-ID header or tenantId query param required"
        )
    return tenant_id


# Type aliases for common dependencies
CurrentTenant = Annotated[UUID | None, Depends(get_current_tenant)]
RequiredTenant = Annotated[UUID, Depends(require_tenant)]
CurrentUserId = Annotated[UUID | None, Depends(get_current_user_id)]