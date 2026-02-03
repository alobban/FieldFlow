"""
Tenant API endpoints.

Provides CRUD operations for tenant management.
"""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.tenant_service import TenantService
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListItem,
)
from app.schemas.base import PaginatedResponse, MessageResponse
from app.core.exceptions import TenantNotFoundException, DuplicateException
from app.core.dependencies import RequiredTenant, CurrentTenant

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT CRUD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "",
    response_model=List[TenantListItem],
    summary="List Tenants",
    description="Get a list of all tenants with pagination.",
)
async def list_tenants(
    skip: Annotated[int, Query(ge=0, description="Records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Max records")] = 20,
    include_inactive: Annotated[bool, Query(description="Include inactive")] = False,
    search: Annotated[str | None, Query(description="Search term")] = None,
    session: AsyncSession = Depends(get_db_session),
) -> List[TenantListItem]:
    """
    List all tenants.
    
    Returns paginated list of tenants with basic info.
    """
    service = TenantService(session)
    
    if search:
        tenants = await service.search(
            query=search,
            include_inactive=include_inactive,
            limit=limit,
        )
    else:
        tenants = await service.get_tenants_for_dropdown(
            include_inactive=include_inactive,
            limit=limit,
        )
    
    return [
        TenantListItem(
            id=t.id,
            business_name=t.business_name,
            slug=t.slug,
            logo_url=t.logo_url,
            is_active=t.is_active,
        )
        for t in tenants
    ]


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Tenant",
    description="Create a new tenant organization.",
)
async def create_tenant(
    data: TenantCreate,
    session: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """
    Create a new tenant.
    
    Note: For full tenant onboarding with owner user,
    use the /bff/web/onboarding/signup endpoint instead.
    """
    service = TenantService(session)
    
    try:
        tenant = await service.create(data)
        return TenantResponse.model_validate(tenant)
    except DuplicateException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.detail),
        )


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get Tenant",
    description="Get a tenant by ID.",
)
async def get_tenant(
    tenant_id: Annotated[UUID, Path(description="Tenant UUID")],
    session: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """
    Get tenant details by ID.
    """
    service = TenantService(session)
    
    try:
        tenant = await service.get_by_id(tenant_id)
        return TenantResponse.model_validate(tenant)
    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )


@router.get(
    "/slug/{slug}",
    response_model=TenantResponse,
    summary="Get Tenant by Slug",
    description="Get a tenant by URL slug.",
)
async def get_tenant_by_slug(
    slug: Annotated[str, Path(description="Tenant slug")],
    session: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """
    Get tenant details by slug.
    """
    service = TenantService(session)
    
    try:
        tenant = await service.get_by_slug(slug)
        return TenantResponse.model_validate(tenant)
    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with slug '{slug}' not found",
        )


@router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update Tenant",
    description="Update tenant details.",
)
async def update_tenant(
    tenant_id: Annotated[UUID, Path(description="Tenant UUID")],
    data: TenantUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """
    Update tenant details.
    
    Only provided fields will be updated.
    """
    service = TenantService(session)
    
    try:
        tenant = await service.update(tenant_id, data)
        return TenantResponse.model_validate(tenant)
    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )
    except DuplicateException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.detail),
        )


@router.delete(
    "/{tenant_id}",
    response_model=MessageResponse,
    summary="Delete Tenant",
    description="Delete a tenant and all associated data.",
)
async def delete_tenant(
    tenant_id: Annotated[UUID, Path(description="Tenant UUID")],
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Delete a tenant.
    
    WARNING: This will delete all associated users and data.
    """
    service = TenantService(session)
    
    try:
        await service.delete(tenant_id)
        return MessageResponse(
            message=f"Tenant {tenant_id} deleted successfully",
            success=True,
        )
    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT STATUS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/{tenant_id}/activate",
    response_model=TenantResponse,
    summary="Activate Tenant",
    description="Activate a tenant.",
)
async def activate_tenant(
    tenant_id: Annotated[UUID, Path(description="Tenant UUID")],
    session: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """
    Activate a tenant.
    """
    service = TenantService(session)
    
    try:
        tenant = await service.activate(tenant_id)
        return TenantResponse.model_validate(tenant)
    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )


@router.post(
    "/{tenant_id}/deactivate",
    response_model=TenantResponse,
    summary="Deactivate Tenant",
    description="Deactivate a tenant.",
)
async def deactivate_tenant(
    tenant_id: Annotated[UUID, Path(description="Tenant UUID")],
    session: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """
    Deactivate a tenant.
    
    Deactivated tenants cannot be accessed by users.
    """
    service = TenantService(session)
    
    try:
        tenant = await service.deactivate(tenant_id)
        return TenantResponse.model_validate(tenant)
    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT VALIDATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/validate/slug/{slug}",
    summary="Validate Slug",
    description="Check if a tenant slug is available.",
)
async def validate_slug(
    slug: Annotated[str, Path(description="Slug to validate")],
    exclude_id: Annotated[UUID | None, Query(description="Tenant to exclude")] = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Validate tenant slug availability.
    """
    service = TenantService(session)
    return await service.validate_slug(slug, exclude_id=exclude_id)


@router.get(
    "/generate/slug",
    summary="Generate Slug",
    description="Generate a unique slug from business name.",
)
async def generate_slug(
    business_name: Annotated[str, Query(description="Business name")],
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Generate a unique slug from business name.
    """
    service = TenantService(session)
    slug = await service.generate_slug(business_name)
    return {"slug": slug, "business_name": business_name}