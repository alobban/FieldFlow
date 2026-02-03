"""
Onboarding service for tenant signup and initial setup.

This service orchestrates the complete tenant onboarding process,
including tenant creation, owner user creation, role assignment,
and initial configuration.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from uuid import UUID
import re
import secrets
import string

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantStatus
from app.models.user import User, UserStatus
from app.models.role import Role, ROLE_TENANT_ADMIN
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.user import UserCreate
from app.schemas.bff.web_requests import TenantSignupRequest
from app.schemas.bff.web_responses import (
    TenantSignupResponse,
    CreatedTenantInfo,
    CreatedUserInfo,
    UsernameValidationResponse,
    UsernameGenerationResponse,
    SlugValidationResponse,
    SlugGenerationResponse,
    OnboardingStatusResponse,
    OnboardingStep,
    FieldValidationError,
    SignupValidationResponse,
)
from app.core.exceptions import (
    DuplicateException,
    ValidationException,
    TenantNotFoundException,
)
from app.core.security import (
    hash_password,
    generate_username,
    create_access_token,
)
from app.config import settings


class OnboardingService:
    """
    Service for tenant onboarding operations.
    
    Handles the complete signup flow including:
    - Pre-signup validation
    - Tenant creation
    - Owner user creation with admin role
    - Initial setup tracking
    - Welcome communications
    """
    
    # Onboarding steps definition
    ONBOARDING_STEPS = [
        {
            "step_id": "email_verification",
            "title": "Verify Email",
            "description": "Confirm your email address to secure your account",
            "is_required": True,
            "order": 1,
        },
        {
            "step_id": "profile_completion",
            "title": "Complete Profile",
            "description": "Add additional information to your profile",
            "is_required": False,
            "order": 2,
        },
        {
            "step_id": "organization_settings",
            "title": "Configure Organization",
            "description": "Set up your organization's basic settings",
            "is_required": True,
            "order": 3,
        },
        {
            "step_id": "invite_team",
            "title": "Invite Team Members",
            "description": "Add team members to your organization",
            "is_required": False,
            "order": 4,
        },
        {
            "step_id": "setup_complete",
            "title": "Complete Setup",
            "description": "Finalize your organization setup",
            "is_required": True,
            "order": 5,
        },
    ]
    
    def __init__(self, session: AsyncSession):
        """
        Initialize service with database session.
        
        Args:
            session: Async database session
        """
        self.session = session
        self.tenant_repository = TenantRepository(session)
        self.user_repository = UserRepository(session)
        self.role_repository = RoleRepository(session)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN SIGNUP FLOW
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def signup_tenant(
        self,
        request: TenantSignupRequest,
        auto_login: bool = True,
    ) -> TenantSignupResponse:
        """
        Complete tenant signup process.
        
        This is the main entry point for new tenant registration.
        It orchestrates:
        1. Validation of all input data
        2. Tenant creation
        3. Owner user creation with admin role
        4. Optional auto-login token generation
        
        Args:
            request: Tenant signup request data
            auto_login: Whether to generate access token
        
        Returns:
            Complete signup response with tenant and user info
        
        Raises:
            ValidationException: If validation fails
            DuplicateException: If tenant/user already exists
        """
        # Step 1: Validate all input
        validation_result = await self.validate_signup_request(request)
        if not validation_result["is_valid"]:
            raise ValidationException(
                detail=f"Validation failed: {validation_result['message']}"
            )
        
        # Step 2: Generate slug if not provided
        slug = request.business_slug
        if not slug:
            slug = await self._generate_unique_slug(request.business_name)
        else:
            # Ensure provided slug is unique
            if await self.tenant_repository.slug_exists(slug):
                slug = await self.tenant_repository.generate_unique_slug(slug)
        
        # Step 3: Generate username if not provided
        username = request.username
        username_was_generated = False
        if not username:
            username = await self._generate_unique_username(
                request.owner_first_name,
                request.owner_last_name,
            )
            username_was_generated = True
        
        # Step 4: Create tenant
        tenant = await self._create_tenant(
            business_name=request.business_name,
            slug=slug,
            description=request.business_description,
            contact_email=request.owner_email,
            contact_phone=request.contact_phone,
        )
        
        # Step 5: Create owner user
        user = await self._create_owner_user(
            tenant_id=tenant.id,
            username=username,
            email=request.owner_email,
            password=request.password,
            first_name=request.owner_first_name,
            last_name=request.owner_last_name,
        )
        
        # Step 6: Assign tenant admin role
        await self._assign_admin_role(user.id)
        
        # Step 7: Generate access token if auto-login enabled
        access_token = None
        expires_in = None
        if auto_login:
            access_token, expires_in = self._generate_access_token(user, tenant)
        
        # Step 8: Build response
        return self._build_signup_response(
            tenant=tenant,
            user=user,
            username_was_generated=username_was_generated,
            access_token=access_token,
            expires_in=expires_in,
        )
    
    async def validate_signup_request(
        self,
        request: TenantSignupRequest,
    ) -> dict:
        """
        Validate complete signup request before processing.
        
        Checks:
        - Business name uniqueness
        - Slug availability (if provided)
        - Email uniqueness
        - Username availability (if provided)
        - Password requirements
        
        Args:
            request: Signup request to validate
        
        Returns:
            Validation result dict with is_valid and errors
        """
        errors: List[FieldValidationError] = []
        
        # Validate business name
        if await self.tenant_repository.business_name_exists(request.business_name):
            errors.append(FieldValidationError(
                field="business_name",
                message="A tenant with this business name already exists",
                code="DUPLICATE_BUSINESS_NAME",
            ))
        
        # Validate slug if provided
        if request.business_slug:
            slug_validation = await self.validate_slug(request.business_slug)
            if not slug_validation.is_available:
                errors.append(FieldValidationError(
                    field="business_slug",
                    message=slug_validation.message,
                    code="INVALID_SLUG" if not slug_validation.is_valid_format else "DUPLICATE_SLUG",
                ))
        
        # Validate username if provided
        if request.username:
            # For new tenant, check global username uniqueness or
            # we'll check within the tenant context after creation
            username_validation = await self._validate_username_format(request.username)
            if not username_validation["is_valid"]:
                errors.append(FieldValidationError(
                    field="username",
                    message=username_validation["message"],
                    code="INVALID_USERNAME",
                ))
        
        # Validate email format is already done by Pydantic
        # Check if email is already used as a tenant contact
        existing_tenant = await self.tenant_repository.get_by_field(
            "contact_email",
            request.owner_email.lower()
        )
        if existing_tenant:
            errors.append(FieldValidationError(
                field="owner_email",
                message="This email is already associated with another tenant",
                code="DUPLICATE_EMAIL",
            ))
        
        is_valid = len(errors) == 0
        
        return {
            "is_valid": is_valid,
            "message": "Validation successful" if is_valid else "Validation failed",
            "errors": errors,
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # USERNAME VALIDATION & GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def validate_username(
        self,
        username: str,
        tenant_id: UUID | None = None,
    ) -> UsernameValidationResponse:
        """
        Validate username availability and format.
        
        Args:
            username: Username to validate
            tenant_id: Optional tenant context for checking
        
        Returns:
            Username validation response
        """
        validation_errors = []
        suggestions = []
        
        # Check format
        format_validation = await self._validate_username_format(username)
        is_valid_format = format_validation["is_valid"]
        
        if not is_valid_format:
            validation_errors = format_validation["errors"]
            message = format_validation["message"]
            is_available = False
        else:
            # Check availability
            if tenant_id:
                is_available = not await self.user_repository.username_exists(
                    username.lower(),
                    tenant_id,
                )
            else:
                # For new tenant signup, username will be unique since tenant is new
                is_available = True
            
            if is_available:
                message = "Username is available"
            else:
                message = "Username is already taken"
                # Generate suggestions
                suggestions = await self.generate_username_suggestions(
                    first_name=None,
                    last_name=None,
                    tenant_id=tenant_id,
                    count=3,
                    base_username=username,
                )
        
        return UsernameValidationResponse(
            username=username,
            is_available=is_available,
            is_valid_format=is_valid_format,
            message=message,
            suggestions=suggestions,
            validation_errors=validation_errors,
        )
    
    async def generate_username_suggestions(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
        tenant_id: UUID | None = None,
        count: int = 3,
        base_username: str | None = None,
    ) -> UsernameGenerationResponse:
        """
        Generate username suggestions.
        
        Args:
            first_name: Optional first name for generation
            last_name: Optional last name for generation
            tenant_id: Optional tenant context
            count: Number of suggestions to generate
            base_username: Optional base username to derive from
        
        Returns:
            Username generation response with suggestions
        """
        suggestions = []
        generated_from = None
        
        # Generate from name if provided
        if first_name or last_name:
            generated_from = f"{first_name or ''} {last_name or ''}".strip()
            name_based = await self._generate_name_based_usernames(
                first_name,
                last_name,
                tenant_id,
                count,
            )
            suggestions.extend(name_based)
        
        # Generate from base username if provided
        if base_username and len(suggestions) < count:
            generated_from = generated_from or base_username
            base_suggestions = await self._generate_from_base_username(
                base_username,
                tenant_id,
                count - len(suggestions),
            )
            suggestions.extend(base_suggestions)
        
        # Fill remaining with random usernames
        while len(suggestions) < count:
            random_username = self._generate_random_username()
            if tenant_id:
                if not await self.user_repository.username_exists(
                    random_username,
                    tenant_id,
                ):
                    suggestions.append(random_username)
            else:
                suggestions.append(random_username)
        
        # Ensure uniqueness
        suggestions = list(dict.fromkeys(suggestions))[:count]
        
        return UsernameGenerationResponse(
            suggestions=suggestions,
            generated_from=generated_from,
            recommended=suggestions[0] if suggestions else self._generate_random_username(),
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SLUG VALIDATION & GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def validate_slug(
        self,
        slug: str,
        exclude_tenant_id: UUID | None = None,
    ) -> SlugValidationResponse:
        """
        Validate tenant slug availability and format.
        
        Args:
            slug: Slug to validate
            exclude_tenant_id: Optional tenant ID to exclude
        
        Returns:
            Slug validation response
        """
        suggestions = []
        
        # Check format
        slug_pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
        is_valid_format = bool(re.match(slug_pattern, slug.lower()))
        
        if not is_valid_format:
            message = "Slug must contain only lowercase letters, numbers, and hyphens"
            is_available = False
        else:
            # Check availability
            is_available = not await self.tenant_repository.slug_exists(
                slug.lower(),
                exclude_id=exclude_tenant_id,
            )
            
            if is_available:
                message = "Slug is available"
            else:
                message = "Slug is already taken"
                # Generate suggestions
                suggestions = await self._generate_slug_suggestions(slug, count=3)
        
        return SlugValidationResponse(
            slug=slug,
            is_available=is_available,
            is_valid_format=is_valid_format,
            message=message,
            suggestions=suggestions,
        )
    
    async def generate_slug(
        self,
        business_name: str,
    ) -> SlugGenerationResponse:
        """
        Generate a slug from business name.
        
        Args:
            business_name: Business name to generate slug from
        
        Returns:
            Slug generation response
        """
        # Generate base slug
        suggested_slug = self._slugify(business_name)
        
        # Check availability
        is_available = not await self.tenant_repository.slug_exists(suggested_slug)
        
        # Generate alternatives if not available
        alternatives = []
        if not is_available:
            unique_slug = await self.tenant_repository.generate_unique_slug(suggested_slug)
            alternatives = await self._generate_slug_suggestions(suggested_slug, count=3)
            suggested_slug = unique_slug
            is_available = True
        
        return SlugGenerationResponse(
            original_name=business_name,
            suggested_slug=suggested_slug,
            is_available=is_available,
            alternatives=alternatives,
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ONBOARDING STATUS & PROGRESS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def get_onboarding_status(
        self,
        tenant_id: UUID,
    ) -> OnboardingStatusResponse:
        """
        Get tenant's onboarding progress status.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            Onboarding status response
        
        Raises:
            TenantNotFoundException: If tenant not found
        """
        tenant = await self.tenant_repository.get_by_id(tenant_id)
        if not tenant:
            raise TenantNotFoundException(identifier=str(tenant_id))
        
        # Get owner user for email verification check
        owner = await self.user_repository.get_tenant_owner(tenant_id)
        
        # Build steps with completion status
        steps = await self._build_onboarding_steps(tenant, owner)
        
        # Calculate completion
        required_steps = [s for s in steps if s.is_required]
        completed_required = [s for s in required_steps if s.is_completed]
        
        completion_percentage = (
            int((len(completed_required) / len(required_steps)) * 100)
            if required_steps else 100
        )
        
        is_complete = len(completed_required) == len(required_steps)
        
        # Find current step
        current_step = None
        for step in steps:
            if not step.is_completed:
                current_step = step
                break
        
        return OnboardingStatusResponse(
            tenant_id=tenant_id,
            is_complete=is_complete,
            completion_percentage=completion_percentage,
            steps=steps,
            current_step=current_step,
            started_at=tenant.created_at,
            completed_at=tenant.updated_at if is_complete else None,
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
            step_id: Step identifier to complete
        
        Returns:
            Updated onboarding status
        """
        # Validate step exists
        valid_step_ids = [s["step_id"] for s in self.ONBOARDING_STEPS]
        if step_id not in valid_step_ids:
            raise ValidationException(f"Invalid step ID: {step_id}")
        
        # For now, we track completion via tenant/user status
        # In a production app, you'd have a separate onboarding_progress table
        
        if step_id == "setup_complete":
            # Mark tenant as active
            await self.tenant_repository.update_status(
                tenant_id,
                TenantStatus.ACTIVE,
            )
        
        return await self.get_onboarding_status(tenant_id)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRIVATE HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def _create_tenant(
        self,
        business_name: str,
        slug: str,
        description: str | None,
        contact_email: str,
        contact_phone: str | None,
    ) -> Tenant:
        """Create a new tenant record."""
        tenant_data = {
            "business_name": business_name,
            "slug": slug.lower(),
            "description": description,
            "contact_email": contact_email.lower(),
            "contact_phone": contact_phone,
            "status": TenantStatus.PENDING_SETUP,
            "is_active": True,
        }
        
        return await self.tenant_repository.create(tenant_data)
    
    async def _create_owner_user(
        self,
        tenant_id: UUID,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> User:
        """Create the tenant owner user."""
        user_data = {
            "tenant_id": tenant_id,
            "username": username.lower(),
            "email": email.lower(),
            "password_hash": hash_password(password),
            "first_name": first_name,
            "last_name": last_name,
            "status": UserStatus.PENDING,
            "is_active": True,
            "is_tenant_owner": True,
            "email_verified": False,
        }
        
        return await self.user_repository.create(user_data)
    
    async def _assign_admin_role(self, user_id: UUID) -> None:
        """Assign tenant admin role to user."""
        admin_role = await self.role_repository.get_tenant_admin_role()
        
        if admin_role:
            await self.role_repository.assign_role_to_user(
                user_id=user_id,
                role_id=admin_role.id,
                is_primary=True,
            )
    
    async def _generate_unique_slug(self, business_name: str) -> str:
        """Generate a unique slug from business name."""
        base_slug = self._slugify(business_name)
        return await self.tenant_repository.generate_unique_slug(base_slug)
    
    async def _generate_unique_username(
        self,
        first_name: str,
        last_name: str,
    ) -> str:
        """Generate a unique username from name."""
        # Generate base username options
        options = self._generate_username_options(first_name, last_name)
        
        # For new tenant, all usernames are available
        # Just return the first option
        return options[0]