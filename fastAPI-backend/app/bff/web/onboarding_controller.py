"""
Onboarding controller for Web BFF.

Handles endpoints related to tenant signup and onboarding:
- New tenant registration
- Username validation and generation
- Slug validation and generation
- Onboarding progress tracking
"""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.onboarding_service import OnboardingService
from app.services.tenant_service import TenantService
from app.services.user_service import UserService
from app.schemas.bff.web_requests import (
    TenantSignupRequest,
    UsernameValidationRequest,
    UsernameGenerationRequest,
    SlugValidationRequest,
    SlugGenerationRequest,
)
from app.schemas.bff.web_responses import (
    TenantSignupResponse,
    UsernameValidationResponse,
    UsernameGenerationResponse,
    SlugValidationResponse,
    SlugGenerationResponse,
    OnboardingStatusResponse,
    SignupValidationResponse,
    FieldValidationError,
    WebBFFSuccessResponse,
)
from app.core.exceptions import (
    ValidationException,
    DuplicateException,
    TenantNotFoundException,
)

router = APIRouter()


class OnboardingController:
    """
    Controller for tenant onboarding operations.
    
    Handles the complete signup flow and onboarding
    progress tracking for the Angular frontend.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize controller with database session.
        
        Args:
            session: Async database session
        """
        self.session = session
        self.onboarding_service = OnboardingService(session)
        self.tenant_service = TenantService(session)
        self.user_service = UserService(session)
    
    async def signup_tenant(
        self,
        request: TenantSignupRequest,
        auto_login: bool = True,
    ) -> TenantSignupResponse:
        """
        Process new tenant signup.
        
        Args:
            request: Tenant signup request
            auto_login: Generate access token for immediate login
        
        Returns:
            Signup response with tenant and user info
        """
        return await self.onboarding_service.signup_tenant(
            request=request,
            auto_login=auto_login,
        )
    
    async def validate_signup(
        self,
        request: TenantSignupRequest,
    ) -> SignupValidationResponse:
        """
        Validate signup request without creating anything.
        
        Args:
            request: Signup request to validate
        
        Returns:
            Validation result
        """
        result = await self.onboarding_service.validate_signup_request(request)
        
        return SignupValidationResponse(
            success=result["is_valid"],
            message=result["message"],
            errors=result.get("errors", []),
        )
    
    async def validate_username(
        self,
        username: str,
        tenant_id: UUID | None = None,
    ) -> UsernameValidationResponse:
        """
        Validate username availability.
        
        Args:
            username: Username to validate
            tenant_id: Optional tenant context
        
        Returns:
            Username validation response
        """
        return await self.onboarding_service.validate_username(
            username=username,
            tenant_id=tenant_id,
        )
    
    async def generate_usernames(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
        tenant_id: UUID | None = None,
        count: int = 3,
    ) -> UsernameGenerationResponse:
        """
        Generate username suggestions.
        
        Args:
            first_name: Optional first name
            last_name: Optional last name
            tenant_id: Optional tenant context
            count: Number of suggestions
        
        Returns:
            Username suggestions response
        """
        return await self.onboarding_service.generate_username_suggestions(
            first_name=first_name,
            last_name=last_name,
            tenant_id=tenant_id,
            count=count,
        )
    
    async def validate_slug(
        self,
        slug: str,
        exclude_tenant_id: UUID | None = None,
    ) -> SlugValidationResponse:
        """
        Validate slug availability.
        
        Args:
            slug: Slug to validate
            exclude_tenant_id: Optional tenant to exclude
        
        Returns:
            Slug validation response
        """
        return await self.onboarding_service.validate_slug(
            slug=slug,
            exclude_tenant_id=exclude_tenant_id,
        )
    
    async def generate_slug(
        self,
        business_name: str,
    ) -> SlugGenerationResponse:
        """
        Generate slug from business name.
        
        Args:
            business_name: Business name
        
        Returns:
            Slug generation response
        """
        return await self.onboarding_service.generate_slug(
            business_name=business_name,
        )
    
    async def get_onboarding_status(
        self,
        tenant_id: UUID,
    ) -> OnboardingStatusResponse:
        """
        Get tenant's onboarding status.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            Onboarding status response
        """
        return await self.onboarding_service.get_onboarding_status(
            tenant_id=tenant_id,
        )
    
    async def complete_onboarding_step(
        self,
        tenant_id: UUID,
        step_id: str,
    ) -> OnboardingStatusResponse:
        """
        Mark an onboarding step as complete.
        
        Args:
            tenant_id: Tenant UUID
            step_id: Step identifier
        
        Returns:
            Updated onboarding status
        """
        return await self.onboarding_service.complete_onboarding_step(
            tenant_id=tenant_id,
            step_id=step_id,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE HANDLERS - TENANT SIGNUP
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/signup",
    response_model=TenantSignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Tenant",
    description="Register a new tenant with owner account. "
                "Creates tenant, owner user with admin role, and optionally "
                "returns access token for immediate login.",
    responses={
        201: {"description": "Tenant created successfully"},
        400: {"description": "Invalid request data"},
        409: {"description": "Tenant or user already exists"},
        422: {"description": "Validation error"},
    },
)
async def signup_tenant(
    request: TenantSignupRequest,
    auto_login: Annotated[
        bool,
        Query(description="Return access token for immediate login")
    ] = True,
    session: AsyncSession = Depends(get_db_session),
) -> TenantSignupResponse:
    """
    Register a new tenant organization.
    
    This endpoint handles the complete tenant signup flow:
    1. Validates all input data
    2. Creates the tenant organization
    3. Creates the owner user account
    4. Assigns tenant_admin role to owner
    5. Optionally generates access token for auto-login
    
    The username and slug can be auto-generated if not provided.
    """
    controller = OnboardingController(session)
    
    try:
        return await controller.signup_tenant(
            request=request,
            auto_login=auto_login,
        )
    except DuplicateException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.detail),
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e.detail),
        )


@router.post(
    "/signup/validate",
    response_model=SignupValidationResponse,
    summary="Validate Signup Request",
    description="Validate signup data without creating anything. "
                "Useful for real-time form validation.",
)
async def validate_signup(
    request: TenantSignupRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SignupValidationResponse:
    """
    Validate signup request before submission.
    
    Performs all validation checks without creating any records.
    Returns detailed field-level errors for form feedback.
    """
    controller = OnboardingController(session)
    return await controller.validate_signup(request)


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE HANDLERS - USERNAME VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/username/validate",
    response_model=UsernameValidationResponse,
    summary="Validate Username",
    description="Check if a username is available and valid.",
)
async def validate_username(
    username: Annotated[
        str,
        Query(
            description="Username to validate",
            min_length=3,
            max_length=50,
        )
    ],
    tenant_id: Annotated[
        UUID | None,
        Query(description="Tenant context for validation")
    ] = None,
    session: AsyncSession = Depends(get_db_session),
) -> UsernameValidationResponse:
    """
    Validate username availability and format.
    
    Used for real-time validation as user types in the form.
    For new tenant signup, tenant_id can be omitted.
    """
    controller = OnboardingController(session)
    return await controller.validate_username(
        username=username,
        tenant_id=tenant_id,
    )


@router.post(
    "/username/validate",
    response_model=UsernameValidationResponse,
    summary="Validate Username (POST)",
    description="Check if a username is available and valid.",
)
async def validate_username_post(
    request: UsernameValidationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> UsernameValidationResponse:
    """
    Validate username availability and format (POST version).
    
    Alternative to GET for more complex validation scenarios.
    """
    controller = OnboardingController(session)
    return await controller.validate_username(
        username=request.username,
        tenant_id=request.tenant_id,
    )


@router.get(
    "/username/generate",
    response_model=UsernameGenerationResponse,
    summary="Generate Username Suggestions",
    description="Generate available username suggestions.",
)
async def generate_usernames(
    first_name: Annotated[
        str | None,
        Query(description="First name for generation", max_length=100)
    ] = None,
    last_name: Annotated[
        str | None,
        Query(description="Last name for generation", max_length=100)
    ] = None,
    tenant_id: Annotated[
        UUID | None,
        Query(description="Tenant context")
    ] = None,
    count: Annotated[
        int,
        Query(description="Number of suggestions", ge=1, le=10)
    ] = 3,
    session: AsyncSession = Depends(get_db_session),
) -> UsernameGenerationResponse:
    """
    Generate username suggestions.
    
    Can generate based on name or completely random.
    All suggestions are guaranteed to be available.
    """
    controller = OnboardingController(session)
    return await controller.generate_usernames(
        first_name=first_name,
        last_name=last_name,
        tenant_id=tenant_id,
        count=count,
    )


@router.post(
    "/username/generate",
    response_model=UsernameGenerationResponse,
    summary="Generate Username Suggestions (POST)",
    description="Generate available username suggestions.",
)
async def generate_usernames_post(
    request: UsernameGenerationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> UsernameGenerationResponse:
    """
    Generate username suggestions (POST version).
    """
    controller = OnboardingController(session)
    return await controller.generate_usernames(
        first_name=request.first_name,
        last_name=request.last_name,
        tenant_id=request.tenant_id,
        count=request.count,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE HANDLERS - SLUG VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/slug/validate",
    response_model=SlugValidationResponse,
    summary="Validate Tenant Slug",
    description="Check if a tenant slug is available and valid.",
)
async def validate_slug(
    slug: Annotated[
        str,
        Query(
            description="Slug to validate",
            min_length=2,
            max_length=100,
        )
    ],
    exclude_tenant_id: Annotated[
        UUID | None,
        Query(description="Tenant ID to exclude (for updates)")
    ] = None,
    session: AsyncSession = Depends(get_db_session),
) -> SlugValidationResponse:
    """
    Validate tenant slug availability and format.
    
    Used for real-time validation as user types in the form.
    """
    controller = OnboardingController(session)
    return await controller.validate_slug(
        slug=slug,
        exclude_tenant_id=exclude_tenant_id,
    )


@router.post(
    "/slug/validate",
    response_model=SlugValidationResponse,
    summary="Validate Tenant Slug (POST)",
    description="Check if a tenant slug is available and valid.",
)
async def validate_slug_post(
    request: SlugValidationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SlugValidationResponse:
    """
    Validate tenant slug availability and format (POST version).
    """
    controller = OnboardingController(session)
    return await controller.validate_slug(
        slug=request.slug,
    )


@router.get(
    "/slug/generate",
    response_model=SlugGenerationResponse,
    summary="Generate Tenant Slug",
    description="Generate a URL-friendly slug from business name.",
)
async def generate_slug(
    business_name: Annotated[
        str,
        Query(
            description="Business name to generate slug from",
            min_length=2,
            max_length=255,
        )
    ],
    session: AsyncSession = Depends(get_db_session),
) -> SlugGenerationResponse:
    """
    Generate a unique slug from business name.
    
    Automatically handles conflicts by appending numbers.
    """
    controller = OnboardingController(session)
    return await controller.generate_slug(business_name=business_name)


@router.post(
    "/slug/generate",
    response_model=SlugGenerationResponse,
    summary="Generate Tenant Slug (POST)",
    description="Generate a URL-friendly slug from business name.",
)
async def generate_slug_post(
    request: SlugGenerationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SlugGenerationResponse:
    """
    Generate a unique slug from business name (POST version).
    """
    controller = OnboardingController(session)
    return await controller.generate_slug(business_name=request.business_name)


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE HANDLERS - ONBOARDING STATUS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/status/{tenant_id}",
    response_model=OnboardingStatusResponse,
    summary="Get Onboarding Status",
    description="Get the onboarding progress for a tenant.",
)
async def get_onboarding_status(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> OnboardingStatusResponse:
    """
    Get tenant's onboarding progress.
    
    Returns list of steps with completion status.
    """
    controller = OnboardingController(session)
    
    try:
        return await controller.get_onboarding_status(tenant_id)
    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )


@router.post(
    "/status/{tenant_id}/steps/{step_id}/complete",
    response_model=OnboardingStatusResponse,
    summary="Complete Onboarding Step",
    description="Mark an onboarding step as complete.",
)
async def complete_onboarding_step(
    tenant_id: UUID,
    step_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> OnboardingStatusResponse:
    """
    Mark an onboarding step as complete.
    
    Returns updated onboarding status.
    """
    controller = OnboardingController(session)
    
    try:
        return await controller.complete_onboarding_step(
            tenant_id=tenant_id,
            step_id=step_id,
        )
    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.detail),
        )


@router.post(
    "/status/{tenant_id}/complete",
    response_model=WebBFFSuccessResponse,
    summary="Complete All Onboarding",
    description="Mark tenant onboarding as fully complete.",
)
async def complete_onboarding(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> WebBFFSuccessResponse:
    """
    Mark tenant onboarding as complete.
    
    Sets tenant status to ACTIVE.
    """
    controller = OnboardingController(session)
    
    try:
        await controller.complete_onboarding_step(
            tenant_id=tenant_id,
            step_id="setup_complete",
        )
        
        return WebBFFSuccessResponse(
            success=True,
            message="Onboarding completed successfully",
        )
    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )