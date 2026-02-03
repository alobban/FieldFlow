"""
User API endpoints.

Provides CRUD operations for user management within tenant context.
"""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status, Path, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.user_service import UserService
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListItem,
)
from app.schemas.base import PaginatedResponse, MessageResponse
from app.core.exceptions import (
    UserNotFoundException,
    DuplicateException,
    ValidationException,
    TenantNotFoundException,
)
from app.core.dependencies import RequiredTenant, CurrentTenant

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# USER CRUD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "",
    response_model=List[UserListItem],
    summary="List Users",
    description="Get a list of users for the current tenant.",
)
async def list_users(
    tenant_id: RequiredTenant,
    skip: Annotated[int, Query(ge=0, description="Records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Max records")] = 20,
    include_inactive: Annotated[bool, Query(description="Include inactive")] = False,
    search: Annotated[str | None, Query(description="Search term")] = None,
    session: AsyncSession = Depends(get_db_session),
) -> List[UserListItem]:
    """
    List users for a tenant.
    
    Requires X-Tenant-ID header or tenantId query parameter.
    """
    service = UserService(session)
    
    if search:
        users = await service.search(
            tenant_id=tenant_id,
            query=search,
            limit=limit,
        )
    else:
        users = await service.get_tenant_users(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
            include_inactive=include_inactive,
        )
    
    return [
        UserListItem(
            id=u.id,
            username=u.username,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            is_active=u.is_active,
            is_tenant_owner=u.is_tenant_owner,
        )
        for u in users
    ]


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description="Create a new user in the tenant.",
)
async def create_user(
    data: UserCreate,
    tenant_id: RequiredTenant,
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Create a new user.
    
    Requires X-Tenant-ID header or tenantId query parameter.
    """
    service = UserService(session)
    
    try:
        user, username_was_generated = await service.create(
            data=data,
            tenant_id=tenant_id,
        )
        
        response = UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status,
            is_active=user.is_active,
            is_tenant_owner=user.is_tenant_owner,
            email_verified=user.email_verified,
            roles=[ur.role.name for ur in user.user_roles] if user.user_roles else [],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        
        return response
    except DuplicateException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.detail),
        )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get User",
    description="Get a user by ID.",
)
async def get_user(
    user_id: Annotated[UUID, Path(description="User UUID")],
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Get user details by ID.
    """
    service = UserService(session)
    
    try:
        user = await service.get_by_id(user_id)
        
        return UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status,
            is_active=user.is_active,
            is_tenant_owner=user.is_tenant_owner,
            email_verified=user.email_verified,
            roles=[ur.role.name for ur in user.user_roles] if user.user_roles else [],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update User",
    description="Update user details.",
)
async def update_user(
    user_id: Annotated[UUID, Path(description="User UUID")],
    data: UserUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Update user details.
    
    Only provided fields will be updated.
    """
    service = UserService(session)
    
    try:
        user = await service.update(user_id, data)
        
        return UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status,
            is_active=user.is_active,
            is_tenant_owner=user.is_tenant_owner,
            email_verified=user.email_verified,
            roles=[ur.role.name for ur in user.user_roles] if user.user_roles else [],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    except DuplicateException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.detail),
        )


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Delete User",
    description="Delete a user.",
)
async def delete_user(
    user_id: Annotated[UUID, Path(description="User UUID")],
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Delete a user.
    
    Cannot delete tenant owner.
    """
    service = UserService(session)
    
    try:
        await service.delete(user_id)
        return MessageResponse(
            message=f"User {user_id} deleted successfully",
            success=True,
        )
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.detail),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# USER STATUS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/{user_id}/verify-email",
    response_model=UserResponse,
    summary="Verify Email",
    description="Mark user's email as verified.",
)
async def verify_email(
    user_id: Annotated[UUID, Path(description="User UUID")],
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Mark user's email as verified.
    """
    service = UserService(session)
    
    try:
        user = await service.verify_email(user_id)
        
        return UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status,
            is_active=user.is_active,
            is_tenant_owner=user.is_tenant_owner,
            email_verified=user.email_verified,
            roles=[ur.role.name for ur in user.user_roles] if user.user_roles else [],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )


@router.post(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate User",
    description="Deactivate a user.",
)
async def deactivate_user(
    user_id: Annotated[UUID, Path(description="User UUID")],
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Deactivate a user.
    
    Cannot deactivate tenant owner.
    """
    service = UserService(session)
    
    try:
        user = await service.deactivate(user_id)
        
        return UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status,
            is_active=user.is_active,
            is_tenant_owner=user.is_tenant_owner,
            email_verified=user.email_verified,
            roles=[ur.role.name for ur in user.user_roles] if user.user_roles else [],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.detail),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# USERNAME VALIDATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/validate/username/{username}",
    summary="Validate Username",
    description="Check if a username is available in the tenant.",
)
async def validate_username(
    username: Annotated[str, Path(description="Username to validate")],
    tenant_id: RequiredTenant,
    exclude_id: Annotated[UUID | None, Query(description="User to exclude")] = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Validate username availability within tenant.
    """
    service = UserService(session)
    return await service.validate_username(
        username=username,
        tenant_id=tenant_id,
        exclude_id=exclude_id,
    )


@router.get(
    "/generate/username",
    summary="Generate Username",
    description="Generate available username suggestions.",
)
async def generate_username(
    tenant_id: RequiredTenant,
    first_name: Annotated[str | None, Query(description="First name")] = None,
    last_name: Annotated[str | None, Query(description="Last name")] = None,
    count: Annotated[int, Query(ge=1, le=10, description="Number of suggestions")] = 3,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Generate available username suggestions.
    """
    service = UserService(session)
    suggestions = await service.generate_username_suggestions(
        first_name=first_name,
        last_name=last_name,
        tenant_id=tenant_id,
        count=count,
    )
    return {
        "suggestions": suggestions,
        "recommended": suggestions[0] if suggestions else None,
    }