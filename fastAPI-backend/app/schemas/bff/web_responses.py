"""
Web BFF Response Schemas - Optimized for Angular Frontend

These schemas define the response payloads sent to the Angular
frontend application. They are structured to minimize additional
processing needed on the frontend.
"""

from datetime import datetime
from typing import List, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class WebBFFBaseResponse(BaseModel):
    """Base response schema for Web BFF endpoints."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# LANDING PAGE RESPONSES
# ═══════════════════════════════════════════════════════════════════════════════


class TenantDropdownItem(WebBFFBaseResponse):
    """
    Minimal tenant info for dropdown/select components.
    
    Optimized for Angular mat-select or ng-select components.
    """
    
    id: UUID = Field(
        description="Tenant unique identifier",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    
    business_name: str = Field(
        description="Display name for dropdown",
        json_schema_extra={"example": "Acme Corporation"},
    )
    
    slug: str = Field(
        description="URL-friendly identifier for routing",
        json_schema_extra={"example": "acme-corporation"},
    )
    
    logo_url: str | None = Field(
        default=None,
        description="Optional logo URL for dropdown item",
        json_schema_extra={"example": "https://cdn.example.com/logos/acme.png"},
    )
    
    # Computed field for Angular dropdown display
    @computed_field
    @property
    def display_label(self) -> str:
        """Formatted label for dropdown display."""
        return self.business_name
    
    @computed_field
    @property
    def route_path(self) -> str:
        """Pre-computed route path for Angular router."""
        return f"/tenant/{self.slug}"


class SignupFormConfig(WebBFFBaseResponse):
    """
    Configuration for the signup form.
    
    Sent to Angular to configure form validation rules,
    ensuring frontend and backend validation match.
    """
    
    # Business name constraints
    business_name_min_length: int = Field(default=2)
    business_name_max_length: int = Field(default=255)
    
    # Username constraints
    username_min_length: int = Field(default=3)
    username_max_length: int = Field(default=50)
    username_pattern: str = Field(
        default=r'^[a-zA-Z][a-zA-Z0-9_]*$',
        description="Regex pattern for username validation",
    )
    username_pattern_message: str = Field(
        default="Username must start with a letter and contain only letters, numbers, and underscores",
    )
    
    # Password constraints
    password_min_length: int = Field(default=8)
    password_max_length: int = Field(default=128)
    password_requirements: List[str] = Field(
        default=[
            "At least one uppercase letter",
            "At least one lowercase letter",
            "At least one digit",
            "At least one special character (!@#$%^&*)",
        ],
        description="Human-readable password requirements",
    )
    
    # Slug constraints
    slug_min_length: int = Field(default=2)
    slug_max_length: int = Field(default=100)
    slug_pattern: str = Field(
        default=r'^[a-z0-9]+(?:-[a-z0-9]+)*$',
        description="Regex pattern for slug validation",
    )
    
    # Feature flags
    allow_custom_username: bool = Field(
        default=True,
        description="Whether users can choose their own username",
    )
    allow_custom_slug: bool = Field(
        default=True,
        description="Whether users can choose their own tenant slug",
    )
    require_phone: bool = Field(
        default=False,
        description="Whether phone number is required",
    )


class LandingPageResponse(WebBFFBaseResponse):
    """
    Complete response for the main landing page.
    
    Contains all data needed to render the landing page:
    - List of existing tenants for dropdown
    - Configuration for signup form
    - UI state hints
    """
    
    # Tenant dropdown data
    tenants: List[TenantDropdownItem] = Field(
        default_factory=list,
        description="Available tenants for dropdown selection",
    )
    
    total_tenants: int = Field(
        description="Total number of active tenants",
        json_schema_extra={"example": 42},
    )
    
    # Form configuration
    signup_form_config: SignupFormConfig = Field(
        default_factory=SignupFormConfig,
        description="Configuration for signup form validation",
    )
    
    # UI hints
    show_tenant_dropdown: bool = Field(
        default=True,
        description="Whether to show tenant selection dropdown",
    )
    
    show_signup_option: bool = Field(
        default=True,
        description="Whether to show 'become a tenant' option",
    )
    
    # Optional messaging
    welcome_message: str | None = Field(
        default="Welcome! Select your organization or create a new one.",
        description="Welcome message to display",
    )
    
    maintenance_message: str | None = Field(
        default=None,
        description="Optional maintenance/alert message",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT SIGNUP RESPONSES
# ═══════════════════════════════════════════════════════════════════════════════


class CreatedUserInfo(WebBFFBaseResponse):
    """Information about the created admin user."""
    
    id: UUID = Field(description="User's unique identifier")
    username: str = Field(description="User's username (may be auto-generated)")
    email: str = Field(description="User's email address")
    first_name: str = Field(description="User's first name")
    last_name: str = Field(description="User's last name")
    
    @computed_field
    @property
    def full_name(self) -> str:
        """User's full name."""
        return f"{self.first_name} {self.last_name}"
    
    # Role information
    roles: List[str] = Field(
        default_factory=lambda: ["tenant_admin"],
        description="Assigned roles",
    )
    
    is_tenant_owner: bool = Field(
        default=True,
        description="Whether this user is the tenant owner",
    )
    
    # Flags
    username_was_generated: bool = Field(
        default=False,
        description="Whether username was auto-generated",
    )
    
    requires_email_verification: bool = Field(
        default=True,
        description="Whether email verification is required",
    )


class CreatedTenantInfo(WebBFFBaseResponse):
    """Information about the created tenant."""
    
    id: UUID = Field(description="Tenant's unique identifier")
    business_name: str = Field(description="Business/organization name")
    slug: str = Field(description="URL-friendly identifier")
    status: str = Field(
        default="pending_setup",
        description="Tenant's initial status",
    )
    
    @computed_field
    @property
    def landing_page_url(self) -> str:
        """URL to tenant's landing page."""
        return f"/tenant/{self.slug}"
    
    @computed_field
    @property
    def dashboard_url(self) -> str:
        """URL to tenant's admin dashboard."""
        return f"/tenant/{self.slug}/dashboard"


class TenantSignupResponse(WebBFFBaseResponse):
    """
    Complete response after successful tenant signup.
    
    Contains all information needed for Angular to:
    1. Display success message
    2. Redirect to appropriate page
    3. Store authentication token (if auto-login enabled)
    """
    
    success: bool = Field(
        default=True,
        description="Whether signup was successful",
    )
    
    message: str = Field(
        default="Tenant created successfully!",
        description="Human-readable success message",
    )
    
    # Created entities
    tenant: CreatedTenantInfo = Field(
        description="Information about created tenant",
    )
    
    user: CreatedUserInfo = Field(
        description="Information about created admin user",
    )
    
    # Authentication (if auto-login enabled)
    access_token: str | None = Field(
        default=None,
        description="JWT access token for immediate login",
    )
    
    token_type: str = Field(
        default="bearer",
        description="Token type",
    )
    
    expires_in: int | None = Field(
        default=None,
        description="Token expiration in seconds",
    )
    
    # Next steps
    redirect_url: str = Field(
        description="Recommended URL to redirect user",
    )
    
    next_steps: List[str] = Field(
        default_factory=lambda: [
            "Verify your email address",
            "Complete your profile",
            "Configure your organization settings",
            "Invite team members",
        ],
        description="List of recommended next steps for user",
    )
    
    # Additional flags
    email_verification_sent: bool = Field(
        default=True,
        description="Whether verification email was sent",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT LANDING PAGE RESPONSE
# ═══════════════════════════════════════════════════════════════════════════════


class TenantRouteInfo(WebBFFBaseResponse):
    """Routing information for a tenant."""
    
    tenant_id: UUID = Field(description="Tenant identifier")
    slug: str = Field(description="URL slug")
    base_path: str = Field(description="Base path for tenant routes")
    
    login_url: str = Field(description="Login page URL")
    dashboard_url: str = Field(description="Dashboard URL")
    
    @computed_field
    @property
    def full_login_url(self) -> str:
        """Full login URL."""
        return f"{self.base_path}/login"


class TenantBranding(WebBFFBaseResponse):
    """Tenant branding information for UI customization."""
    
    logo_url: str | None = Field(default=None, description="Logo URL")
    primary_color: str | None = Field(default=None, description="Primary brand color")
    secondary_color: str | None = Field(default=None, description="Secondary brand color")
    favicon_url: str | None = Field(default=None, description="Favicon URL")


class TenantLandingPageResponse(WebBFFBaseResponse):
    """
    Response for a specific tenant's landing page.
    
    Used when user selects a tenant from dropdown or
    navigates directly to /tenant/{slug}.
    """
    
    # Basic tenant info
    tenant_id: UUID = Field(description="Tenant identifier")
    business_name: str = Field(description="Business name for display")
    slug: str = Field(description="URL slug")
    description: str | None = Field(default=None, description="Tenant description")
    
    # Status
    is_active: bool = Field(description="Whether tenant is active")
    status: str = Field(description="Tenant status")
    
    # Branding
    branding: TenantBranding = Field(
        default_factory=TenantBranding,
        description="Tenant branding configuration",
    )
    
    # Routing
    routes: TenantRouteInfo = Field(description="Routing information")
    
    # Features
    allow_registration: bool = Field(
        default=True,
        description="Whether new user registration is allowed",
    )
    
    allow_password_reset: bool = Field(
        default=True,
        description="Whether password reset is available",
    )
    
    # SSO options (if applicable)
    sso_enabled: bool = Field(
        default=False,
        description="Whether SSO is enabled",
    )
    
    sso_providers: List[str] = Field(
        default_factory=list,
        description="Available SSO providers",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# USERNAME VALIDATION RESPONSES
# ═══════════════════════════════════════════════════════════════════════════════


class UsernameValidationResponse(WebBFFBaseResponse):
    """
    Response for username availability check.
    
    Used for real-time form validation in Angular.
    """
    
    username: str = Field(description="The username that was checked")
    
    is_available: bool = Field(
        description="Whether username is available",
    )
    
    is_valid_format: bool = Field(
        description="Whether username format is valid",
    )
    
    message: str = Field(
        description="Human-readable status message",
    )
    
    suggestions: List[str] = Field(
        default_factory=list,
        description="Alternative username suggestions if not available",
    )
    
    # Detailed validation info for UI feedback
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors if format is invalid",
    )


class UsernameGenerationResponse(WebBFFBaseResponse):
    """
    Response containing generated username suggestions.
    
    Provides multiple options for user to choose from.
    """
    
    suggestions: List[str] = Field(
        description="List of available username suggestions",
    )
    
    generated_from: str | None = Field(
        default=None,
        description="What the usernames were generated from",
    )
    
    # Pre-selected recommendation
    recommended: str = Field(
        description="Recommended/primary suggestion",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SLUG VALIDATION RESPONSES
# ═══════════════════════════════════════════════════════════════════════════════


class SlugValidationResponse(WebBFFBaseResponse):
    """Response for tenant slug availability check."""
    
    slug: str = Field(description="The slug that was checked")
    is_available: bool = Field(description="Whether slug is available")
    is_valid_format: bool = Field(description="Whether slug format is valid")
    message: str = Field(description="Human-readable status message")
    
    suggestions: List[str] = Field(
        default_factory=list,
        description="Alternative slug suggestions if not available",
    )


class SlugGenerationResponse(WebBFFBaseResponse):
    """Response containing generated slug from business name."""
    
    original_name: str = Field(description="Original business name")
    suggested_slug: str = Field(description="Generated slug")
    is_available: bool = Field(description="Whether suggested slug is available")
    
    alternatives: List[str] = Field(
        default_factory=list,
        description="Alternative slugs if primary is taken",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION ERROR RESPONSES
# ═══════════════════════════════════════════════════════════════════════════════


class FieldValidationError(WebBFFBaseResponse):
    """Validation error for a specific field."""
    
    field: str = Field(
        description="Field name that has error",
        json_schema_extra={"example": "username"},
    )
    
    message: str = Field(
        description="Human-readable error message",
        json_schema_extra={"example": "Username is already taken"},
    )
    
    code: str = Field(
        description="Error code for programmatic handling",
        json_schema_extra={"example": "DUPLICATE_USERNAME"},
    )
    
    # For Angular form control binding
    @computed_field
    @property
    def form_control_name(self) -> str:
        """Convert field name to Angular form control name (camelCase)."""
        parts = self.field.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])


class SignupValidationResponse(WebBFFBaseResponse):
    """
    Response when signup validation fails.
    
    Structured for easy binding to Angular reactive forms.
    """
    
    success: bool = Field(default=False)
    
    message: str = Field(
        default="Validation failed",
        description="General error message",
    )
    
    errors: List[FieldValidationError] = Field(
        default_factory=list,
        description="List of field-specific errors",
    )
    
    @computed_field
    @property
    def error_count(self) -> int:
        """Total number of validation errors."""
        return len(self.errors)
    
    @computed_field
    @property
    def error_map(self) -> dict[str, str]:
        """Map of field names to error messages for Angular forms."""
        return {error.field: error.message for error in self.errors}


# ═══════════════════════════════════════════════════════════════════════════════
# ONBOARDING STATUS RESPONSE
# ═══════════════════════════════════════════════════════════════════════════════


class OnboardingStep(WebBFFBaseResponse):
    """Individual onboarding step status."""
    
    step_id: str = Field(description="Step identifier")
    title: str = Field(description="Step title")
    description: str = Field(description="Step description")
    is_completed: bool = Field(description="Whether step is completed")
    is_current: bool = Field(description="Whether this is the current step")
    is_required: bool = Field(default=True, description="Whether step is required")
    order: int = Field(description="Step order")
    
    action_url: str | None = Field(
        default=None,
        description="URL to complete this step",
    )


class OnboardingStatusResponse(WebBFFBaseResponse):
    """
    Response for tenant onboarding status.
    
    Tracks progress through initial setup steps.
    """
    
    tenant_id: UUID = Field(description="Tenant identifier")
    
    is_complete: bool = Field(
        description="Whether all required steps are complete",
    )
    
    completion_percentage: int = Field(
        ge=0,
        le=100,
        description="Overall completion percentage",
    )
    
    steps: List[OnboardingStep] = Field(
        description="List of onboarding steps",
    )
    
    current_step: OnboardingStep | None = Field(
        default=None,
        description="Current step to complete",
    )
    
    # Time tracking
    started_at: datetime = Field(description="When onboarding started")
    completed_at: datetime | None = Field(
        default=None,
        description="When onboarding was completed",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GENERIC RESPONSES
# ═══════════════════════════════════════════════════════════════════════════════


class WebBFFSuccessResponse(WebBFFBaseResponse):
    """Generic success response."""
    
    success: bool = Field(default=True)
    message: str = Field(description="Success message")
    data: Any | None = Field(default=None, description="Optional response data")


class WebBFFErrorResponse(WebBFFBaseResponse):
    """Generic error response."""
    
    success: bool = Field(default=False)
    message: str = Field(description="Error message")
    error_code: str | None = Field(default=None, description="Error code")
    details: List[str] = Field(
        default_factory=list,
        description="Additional error details",
    )
    
    # For Angular HTTP interceptor
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When error occurred",
    )