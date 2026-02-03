"""
Role API endpoints.

Provides endpoints for role management and user-role assignments.
"""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, ConfigDict

from app.database import get_db_session
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.models.role import Role, UserRole
from app.schemas.base import MessageResponse
from app.core.exceptions import UserNotFoundException

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class RoleResponse(BaseModel):
    """Role response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(description="Role unique identifier")
    name: str = Field(description="Role name (system identifier)")
    display_name: str = Field(description="Human-readable role name")
    description: str | None = Field(default=None, description="Role description")
    is_system_role: bool = Field(description="Whether this is a system-defined role")


class RoleCreate(BaseModel):
    """Role creation request schema."""
    
    name: str = Field(
        min_length=2,
        max_length=50,
        pattern=r'^[a-z][a-z0-9_]*$',
        description="Role name (lowercase, underscores allowed)",
    )
    display_name: str = Field(
        min_length=2,
        max_length=100,
        description="Human-readable display name",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Role description",
    )


class RoleUpdate(BaseModel):
    """Role update request schema."""
    
    display_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    description: str | None = Field(
        default=None,
        max_length=500,
    )


class UserRoleAssignment(BaseModel):
    """User role assignment request."""
    
    user_id: UUID = Field(description="User to assign role to")
    role_id: UUID = Field(description="Role to assign")
    is_primary: bool = Field(
        default=False,
        description="Set as user's primary role",
    )


class UserRoleRemoval(BaseModel):
    """User role removal request."""
    
    user_id: UUID = Field(description="User to remove role from")
    role_id: UUID = Field(description="Role to remove")


class RoleAssignmentResponse(BaseModel):
    """Role assignment response."""
    
    user_id: UUID = Field(description="User ID")
    role_id: UUID = Field(description="Role ID")
    role_name: str = Field(description="Role name")
    is_primary: bool = Field(description="Whether this is the primary role")
    message: str = Field(description="Operation result message")


class UserRoleResponse(BaseModel):
    """User's role information."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(description="UserRole assignment ID")
    user_id: UUID = Field(description="User ID")
    role_id: UUID = Field(description="Role ID")
    role_name: str = Field(description="Role name")
    role_display_name: str = Field(description="Role display name")
    is_primary: bool = Field(description="Whether this is the primary role")


class UserRolesListResponse(BaseModel):
    """List of user's roles."""
    
    user_id: UUID = Field(description="User ID")
    roles: List[UserRoleResponse] = Field(description="User's assigned roles")
    primary_role: str | None = Field(description="Name of primary role")


class BulkRoleAssignment(BaseModel):
    """Bulk role assignment request."""
    
    user_ids: List[UUID] = Field(
        min_length=1,
        max_length=100,
        description="List of user IDs to assign role to",
    )
    role_id: UUID = Field(description="Role to assign")


class BulkRoleAssignmentResponse(BaseModel):
    """Bulk role assignment response."""
    
    role_id: UUID = Field(description="Role that was assigned")
    role_name: str = Field(description="Role name")
    successful: List[UUID] = Field(description="User IDs successfully assigned")
    failed: List[dict] = Field(description="Failed assignments with reasons")
    total_processed: int = Field(description="Total users processed")
    success_count: int = Field(description="Number of successful assignments")
    failure_count: int = Field(description="Number of failed assignments")


# ═══════════════════════════════════════════════════════════════════════════════
# ROLE CRUD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "",
    response_model=List[RoleResponse],
    summary="List Roles",
    description="Get all available roles.",
)
async def list_roles(
    system_only: Annotated[
        bool,
        Query(description="Return only system-defined roles")
    ] = False,
    session: AsyncSession = Depends(get_db_session),
) -> List[RoleResponse]:
    """
    List all available roles.
    
    Can filter to show only system-defined roles.
    """
    repository = RoleRepository(session)
    
    if system_only:
        roles = await repository.get_system_roles()
    else:
        roles = await repository.get_all_roles()
    
    return [RoleResponse.model_validate(role) for role in roles]


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Role",
    description="Create a new custom role.",
)
async def create_role(
    data: RoleCreate,
    session: AsyncSession = Depends(get_db_session),
) -> RoleResponse:
    """
    Create a new custom role.
    
    System roles cannot be created through this endpoint.
    """
    repository = RoleRepository(session)
    
    # Check if role name already exists
    existing = await repository.get_by_name(data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role with name '{data.name}' already exists",
        )
    
    # Create role
    role_data = {
        "name": data.name.lower(),
        "display_name": data.display_name,
        "description": data.description,
        "is_system_role": False,
    }
    
    role = await repository.create(role_data)
    return RoleResponse.model_validate(role)


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Get Role",
    description="Get a role by ID.",
)
async def get_role(
    role_id: Annotated[UUID, Path(description="Role UUID")],
    session: AsyncSession = Depends(get_db_session),
) -> RoleResponse:
    """
    Get role details by ID.
    """
    repository = RoleRepository(session)
    role = await repository.get_by_id(role_id)
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found",
        )
    
    return RoleResponse.model_validate(role)


@router.get(
    "/name/{name}",
    response_model=RoleResponse,
    summary="Get Role by Name",
    description="Get a role by its name.",
)
async def get_role_by_name(
    name: Annotated[str, Path(description="Role name")],
    session: AsyncSession = Depends(get_db_session),
) -> RoleResponse:
    """
    Get role details by name.
    """
    repository = RoleRepository(session)
    role = await repository.get_by_name(name.lower())
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{name}' not found",
        )
    
    return RoleResponse.model_validate(role)


@router.patch(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Update Role",
    description="Update a role's display name or description.",
)
async def update_role(
    role_id: Annotated[UUID, Path(description="Role UUID")],
    data: RoleUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> RoleResponse:
    """
    Update a role.
    
    System role names cannot be changed.
    Only display_name and description can be updated.
    """
    repository = RoleRepository(session)
    
    # Get existing role
    role = await repository.get_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found",
        )
    
    # Update role
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        updated_role = await repository.update(role_id, update_data)
        return RoleResponse.model_validate(updated_role)
    
    return RoleResponse.model_validate(role)


@router.delete(
    "/{role_id}",
    response_model=MessageResponse,
    summary="Delete Role",
    description="Delete a custom role.",
)
async def delete_role(
    role_id: Annotated[UUID, Path(description="Role UUID")],
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Delete a role.
    
    System roles cannot be deleted.
    Role must not be assigned to any users.
    """
    repository = RoleRepository(session)
    
    # Get role
    role = await repository.get_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found",
        )
    
    # Prevent deletion of system roles
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System roles cannot be deleted",
        )
    
    # Check if role is assigned to any users
    if role.user_roles and len(role.user_roles) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role '{role.name}' - it is assigned to {len(role.user_roles)} user(s)",
        )
    
    # Delete role
    await repository.delete(role_id)
    
    return MessageResponse(
        message=f"Role '{role.name}' deleted successfully",
        success=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ROLE ASSIGNMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/assign",
    response_model=RoleAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign Role to User",
    description="Assign a role to a user.",
)
async def assign_role(
    assignment: UserRoleAssignment,
    session: AsyncSession = Depends(get_db_session),
) -> RoleAssignmentResponse:
    """
    Assign a role to a user.
    
    A user can have multiple roles.
    Set is_primary=true to make this the user's primary role.
    """
    role_repository = RoleRepository(session)
    user_repository = UserRepository(session)
    
    # Verify user exists
    user = await user_repository.get_by_id(assignment.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {assignment.user_id} not found",
        )
    
    # Verify role exists
    role = await role_repository.get_by_id(assignment.role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {assignment.role_id} not found",
        )
    
    # Check if user already has this role
    if await role_repository.user_has_role(assignment.user_id, role.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already has role '{role.name}'",
        )
    
    # Assign role
    user_role = await role_repository.assign_role_to_user(
        user_id=assignment.user_id,
        role_id=assignment.role_id,
        is_primary=assignment.is_primary,
    )
    
    # If setting as primary, update other roles
    if assignment.is_primary:
        await role_repository.set_primary_role(
            user_id=assignment.user_id,
            role_id=assignment.role_id,
        )
    
    return RoleAssignmentResponse(
        user_id=assignment.user_id,
        role_id=assignment.role_id,
        role_name=role.name,
        is_primary=assignment.is_primary,
        message=f"Role '{role.display_name}' assigned successfully",
    )


@router.delete(
    "/assign",
    response_model=MessageResponse,
    summary="Remove Role from User",
    description="Remove a role assignment from a user.",
)
async def remove_role(
    removal: UserRoleRemoval,
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Remove a role from a user.
    
    Users must have at least one role.
    """
    role_repository = RoleRepository(session)
    user_repository = UserRepository(session)
    
    # Verify user exists
    user = await user_repository.get_with_roles(removal.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {removal.user_id} not found",
        )
    
    # Verify role exists
    role = await role_repository.get_by_id(removal.role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {removal.role_id} not found",
        )
    
    # Check if user has this role
    if not await role_repository.user_has_role(removal.user_id, role.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User does not have role '{role.name}'",
        )
    
    # Ensure user will have at least one role remaining
    current_roles = await role_repository.get_user_roles(removal.user_id)
    if len(current_roles) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove user's only role. Assign another role first.",
        )
    
    # Remove role
    removed = await role_repository.remove_role_from_user(
        user_id=removal.user_id,
        role_id=removal.role_id,
    )
    
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove role",
        )
    
    return MessageResponse(
        message=f"Role '{role.display_name}' removed from user",
        success=True,
    )


@router.post(
    "/assign/bulk",
    response_model=BulkRoleAssignmentResponse,
    summary="Bulk Assign Role",
    description="Assign a role to multiple users at once.",
)
async def bulk_assign_role(
    assignment: BulkRoleAssignment,
    session: AsyncSession = Depends(get_db_session),
) -> BulkRoleAssignmentResponse:
    """
    Assign a role to multiple users.
    
    Returns details of successful and failed assignments.
    """
    role_repository = RoleRepository(session)
    user_repository = UserRepository(session)
    
    # Verify role exists
    role = await role_repository.get_by_id(assignment.role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {assignment.role_id} not found",
        )
    
    successful = []
    failed = []
    
    for user_id in assignment.user_ids:
        try:
            # Verify user exists
            user = await user_repository.get_by_id(user_id)
            if not user:
                failed.append({
                    "user_id": str(user_id),
                    "reason": "User not found",
                })
                continue
            
            # Check if user already has role
            if await role_repository.user_has_role(user_id, role.name):
                failed.append({
                    "user_id": str(user_id),
                    "reason": "User already has this role",
                })
                continue
            
            # Assign role
            await role_repository.assign_role_to_user(
                user_id=user_id,
                role_id=assignment.role_id,
                is_primary=False,
            )
            
            successful.append(user_id)
            
        except Exception as e:
            failed.append({
                "user_id": str(user_id),
                "reason": str(e),
            })
    
    return BulkRoleAssignmentResponse(
        role_id=assignment.role_id,
        role_name=role.name,
        successful=successful,
        failed=failed,
        total_processed=len(assignment.user_ids),
        success_count=len(successful),
        failure_count=len(failed),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# USER ROLES QUERY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/users/{user_id}",
    response_model=UserRolesListResponse,
    summary="Get User's Roles",
    description="Get all roles assigned to a user.",
)
async def get_user_roles(
    user_id: Annotated[UUID, Path(description="User UUID")],
    session: AsyncSession = Depends(get_db_session),
) -> UserRolesListResponse:
    """
    Get all roles assigned to a user.
    """
    role_repository = RoleRepository(session)
    user_repository = UserRepository(session)
    
    # Verify user exists
    user = await user_repository.get_with_roles(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    
    # Get user's roles
    user_roles = await role_repository.get_user_roles(user_id)
    
    roles = []
    primary_role = None
    
    for ur in user_roles:
        role = await role_repository.get_by_id(ur.role_id)
        if role:
            roles.append(UserRoleResponse(
                id=ur.id,
                user_id=ur.user_id,
                role_id=ur.role_id,
                role_name=role.name,
                role_display_name=role.display_name,
                is_primary=ur.is_primary,
            ))
            
            if ur.is_primary:
                primary_role = role.name
    
    return UserRolesListResponse(
        user_id=user_id,
        roles=roles,
        primary_role=primary_role,
    )


@router.put(
    "/users/{user_id}/primary/{role_id}",
    response_model=MessageResponse,
    summary="Set Primary Role",
    description="Set a user's primary role.",
)
async def set_primary_role(
    user_id: Annotated[UUID, Path(description="User UUID")],
    role_id: Annotated[UUID, Path(description="Role UUID to set as primary")],
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Set a user's primary role.
    
    The role must already be assigned to the user.
    """
    role_repository = RoleRepository(session)
    user_repository = UserRepository(session)
    
    # Verify user exists
    user = await user_repository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    
    # Verify role exists
    role = await role_repository.get_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found",
        )
    
    # Verify user has this role
    if not await role_repository.user_has_role(user_id, role.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User does not have role '{role.name}'. Assign the role first.",
        )
    
    # Set as primary
    await role_repository.set_primary_role(user_id, role_id)
    
    return MessageResponse(
        message=f"Role '{role.display_name}' set as primary role for user",
        success=True,
    )


@router.get(
    "/{role_id}/users",
    response_model=List[UUID],
    summary="Get Users with Role",
    description="Get all user IDs that have a specific role.",
)
async def get_users_with_role(
    role_id: Annotated[UUID, Path(description="Role UUID")],
    tenant_id: Annotated[UUID | None, Query(description="Filter by tenant")] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max results")] = 100,
    session: AsyncSession = Depends(get_db_session),
) -> List[UUID]:
    """
    Get all users that have a specific role.
    
    Optionally filter by tenant.
    """
    role_repository = RoleRepository(session)
    user_repository = UserRepository(session)
    
    # Verify role exists
    role = await role_repository.get_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found",
        )
    
    # Get users with this role
    if tenant_id:
        users = await user_repository.get_users_by_role(
            tenant_id=tenant_id,
            role_name=role.name,
            limit=limit,
        )
        return [user.id for user in users]
    else:
        # Get all user_roles for this role
        user_roles = role.user_roles or []
        return [ur.user_id for ur in user_roles][:limit]


# ═══════════════════════════════════════════════════════════════════════════════
# ROLE CHECK ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/check/{user_id}/{role_name}",
    summary="Check User Has Role",
    description="Check if a user has a specific role.",
)
async def check_user_has_role(
    user_id: Annotated[UUID, Path(description="User UUID")],
    role_name: Annotated[str, Path(description="Role name to check")],
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Check if a user has a specific role.
    
    Returns boolean indicating if user has the role.
    """
    role_repository = RoleRepository(session)
    user_repository = UserRepository(session)
    
    # Verify user exists
    user = await user_repository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    
    has_role = await role_repository.user_has_role(user_id, role_name.lower())
    
    return {
        "user_id": str(user_id),
        "role_name": role_name,
        "has_role": has_role,
    }


@router.post(
    "/check/{user_id}",
    summary="Check User Has Any Role",
    description="Check if a user has any of the specified roles.",
)
async def check_user_has_any_role(
    user_id: Annotated[UUID, Path(description="User UUID")],
    role_names: Annotated[List[str], Body(description="Role names to check")],
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Check if a user has any of the specified roles.
    
    Returns which roles the user has from the provided list.
    """
    role_repository = RoleRepository(session)
    user_repository = UserRepository(session)
    
    # Verify user exists
    user = await user_repository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    
    # Check each role
    results = {}
    has_any = False
    
    for role_name in role_names:
        has_role = await role_repository.user_has_role(user_id, role_name.lower())
        results[role_name] = has_role
        if has_role:
            has_any = True
    
    return {
        "user_id": str(user_id),
        "has_any": has_any,
        "roles_checked": results,
        "matching_roles": [name for name, has in results.items() if has],
    }