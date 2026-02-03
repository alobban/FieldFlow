"""
Landing page controller for Web BFF.

Handles endpoints related to the main landing page:
- Fetching tenant list for dropdown
- Tenant search/autocomplete
- Tenant selection and routing
"""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.tenant_service import TenantService
from app.schemas.bff.web_requests import (
    LandingPageRequest,
    TenantSelectionRequest,
    TenantSearchRequest,
)
from app.schemas.bff.web_responses import (
    LandingPageResponse,
    TenantDropdownItem,
    TenantLandingPageResponse,
    TenantRouteInfo,
    TenantBranding,
    SignupFormConfig,
)
from app.core.exceptions import TenantNotFoundException

router = APIRouter()


class LandingController:
    """
    Controller for landing page operations.
    
    Provides methods for handling landing page requests
    optimized for the Angular frontend.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize controller with database session.
        
        Args:
            session: Async database session
        """
        self.session = session
        self.tenant_service = TenantService(session)
    
    async def get_landing_page_data(
        self,
        include_inactive: bool = False,
        search_term: str | None = None,
        limit: int = 50,
    ) -> LandingPageResponse:
        """
        Get all data needed for the landing page.
        
        Args:
            include_inactive: Include inactive tenants
            search_term: Optional search filter
            limit: Maximum tenants to return
        
        Returns:
            Complete landing page response
        """
        # Get tenants for dropdown
        tenants = await self.tenant_service.get_tenants_for_dropdown(
            include_inactive=include_inactive,
            search_term=search_term,
            limit=limit,
        )
        
        # Convert to dropdown items
        dropdown_items = [
            TenantDropdownItem(
                id=tenant.id,
                business_name=tenant.business_name,
                slug=tenant.slug,
                logo_url=tenant.logo_url,
            )
            for tenant in tenants
        ]
        
        # Get total count
        total_tenants = await self.tenant_service.count_active()
        
        return LandingPageResponse(
            tenants=dropdown_items,
            total_tenants=total_tenants,
            signup_form_config=SignupFormConfig(),
            show_tenant_dropdown=True,
            show_signup_option=True,
            welcome_message="Welcome! Select your organization or create a new one.",
        )
    
    async def search_tenants(
        self,
        query: str,
        include_inactive: bool = False,
        limit: int = 10,
    ) -> List[TenantDropdownItem]:
        """
        Search tenants for autocomplete.
        
        Args:
            query: Search query string
            include_inactive: Include inactive tenants
            limit: Maximum results
        
        Returns:
            List of matching tenant dropdown items
        """
        tenants = await self.tenant_service.search(
            query=query,
            include_inactive=include_inactive,
            limit=limit,
        )
        
        return [
            TenantDropdownItem(
                id=tenant.id,
                business_name=tenant.business_name,
                slug=tenant.slug,
                logo_url=tenant.logo_url,
            )
            for tenant in tenants
        ]
    
    async def get_tenant_landing_page(
        self,
        tenant_id: UUID | None = None,
        tenant_slug: str | None = None,
    ) -> TenantLandingPageResponse:
        """
        Get data for a specific tenant's landing page.
        
        Args:
            tenant_id: Tenant UUID
            tenant_slug: Tenant slug (alternative to ID)
        
        Returns:
            Tenant landing page response
        
        Raises:
            TenantNotFoundException: If tenant not found
        """
        if tenant_id:
            tenant = await self.tenant_service.get_by_id(tenant_id)
        elif tenant_slug:
            tenant = await self.tenant_service.get_by_slug(tenant_slug)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either tenant_id or tenant_slug must be provided",
            )
        
        # Build route info
        base_path = f"/tenant/{tenant.slug}"
        routes = TenantRouteInfo(
            tenant_id=tenant.id,
            slug=tenant.slug,
            base_path=base_path,
            login_url=f"{base_path}/login",
            dashboard_url=f"{base_path}/dashboard",
        )
        
        # Build branding
        branding = TenantBranding(
            logo_url=tenant.logo_url,
            primary_color=None,  # Could be stored in tenant settings
            secondary_color=None,
            favicon_url=None,
        )
        
        return TenantLandingPageResponse(
            tenant_id=tenant.id,
            business_name=tenant.business_name,
            slug=tenant.slug,
            description=tenant.description,
            is_active=tenant.is_active,
            status=tenant.status.value,
            branding=branding,
            routes=routes,
            allow_registration=True,
            allow_password_reset=True,
            sso_enabled=False,
            sso_providers=[],
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "",
    response_model=LandingPageResponse,
    summary="Get Landing Page Data",
    description="Retrieve all data needed to render the main landing page, "
                "including tenant dropdown list and signup form configuration.",
)
async def get_landing_page(
    include_inactive: Annotated[
        bool,
        Query(description="Include inactive tenants in dropdown")
    ] = False,
    search_term: Annotated[
        str | None,
        Query(description="Filter tenants by name", max_length=100)
    ] = None,
    limit: Annotated[
        int,
        Query(description="Maximum tenants to return", ge=1, le=200)
    ] = 50,
    session: AsyncSession = Depends(get_db_session),
) -> LandingPageResponse:
    """
    Get landing page data for Angular frontend.
    
    Returns:
    - List of tenants for dropdown selection
    - Signup form configuration
    - UI display flags
    """
    controller = LandingController(session)
    return await controller.get_landing_page_data(
        include_inactive=include_inactive,
        search_term=search_term,
        limit=limit,
    )


@router.get(
    "/tenants/search",
    response_model=List[TenantDropdownItem],
    summary="Search Tenants",
    description="Search tenants for autocomplete/typeahead functionality.",
)
async def search_tenants(
    query: Annotated[
        str,
        Query(description="Search query", min_length=1, max_length=100)
    ],
    include_inactive: Annotated[
        bool,
        Query(description="Include inactive tenants")
    ] = False,
    limit: Annotated[
        int,
        Query(description="Maximum results", ge=1, le=50)
    ] = 10,
    session: AsyncSession = Depends(get_db_session),
) -> List[TenantDropdownItem]:
    """
    Search tenants by name for autocomplete.
    
    Used for typeahead functionality in the tenant dropdown.
    """
    controller = LandingController(session)
    return await controller.search_tenants(
        query=query,
        include_inactive=include_inactive,
        limit=limit,
    )


@router.get(
    "/tenants/dropdown",
    response_model=List[TenantDropdownItem],
    summary="Get Tenants for Dropdown",
    description="Get list of tenants formatted for dropdown selection.",
)
async def get_tenants_dropdown(
    include_inactive: Annotated[
        bool,
        Query(description="Include inactive tenants")
    ] = False,
    limit: Annotated[
        int,
        Query(description="Maximum tenants to return", ge=1, le=200)
    ] = 50,
    session: AsyncSession = Depends(get_db_session),
) -> List[TenantDropdownItem]:
    """
    Get tenants for dropdown selection.
    
    Returns minimal tenant info optimized for dropdown components.
    """
    controller = LandingController(session)
    return await controller.search_tenants(
        query="",  # Empty query returns all
        include_inactive=include_inactive,
        limit=limit,
    )


@router.post(
    "/tenants/select",
    response_model=TenantLandingPageResponse,
    summary="Select Tenant",
    description="Get tenant details after user selects from dropdown.",
)
async def select_tenant(
    request: TenantSelectionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TenantLandingPageResponse:
    """
    Handle tenant selection from dropdown.
    
    Returns the selected tenant's landing page data for routing.
    """
    controller = LandingController(session)
    return await controller.get_tenant_landing_page(
        tenant_id=request.tenant_id,
        tenant_slug=request.tenant_slug,
    )


@router.get(
    "/tenants/{identifier}",
    response_model=TenantLandingPageResponse,
    summary="Get Tenant Landing Page",
    description="Get data for a specific tenant's landing page by ID or slug.",
)
async def get_tenant_landing(
    identifier: str,
    session: AsyncSession = Depends(get_db_session),
) -> TenantLandingPageResponse:
    """
    Get tenant landing page data.
    
    The identifier can be either a UUID or a slug.
    Used when navigating directly to /tenant/{slug}.
    """
    controller = LandingController(session)
    
    # Try to parse as UUID
    try:
        tenant_id = UUID(identifier)
        return await controller.get_tenant_landing_page(tenant_id=tenant_id)
    except ValueError:
        # Not a UUID, treat as slug
        return await controller.get_tenant_landing_page(tenant_slug=identifier)


@router.get(
    "/config/signup-form",
    response_model=SignupFormConfig,
    summary="Get Signup Form Configuration",
    description="Get validation rules and configuration for the signup form.",
)
async def get_signup_form_config() -> SignupFormConfig:
    """
    Get signup form configuration.
    
    Returns validation rules that should match frontend validation.
    """
    return SignupFormConfig()