"""
Web BFF Request Schemas - Optimized for Angular Frontend

These schemas define the expected request payloads from the Angular
frontend application. They include validation rules that match
frontend form validation for consistency.
"""

from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
import re


class WebBFFBaseRequest(BaseModel):
    """Base request schema for Web BFF endpoints."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        use_enum_values=True,
        populate_by_name=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# LANDING PAGE REQUESTS
# ═══════════════════════════════════════════════════════════════════════════════


class LandingPageRequest(WebBFFBaseRequest):
    """
    Request parameters for loading the landing page.
    
    Used when Angular app initializes to fetch available tenants
    for the dropdown selector.
    """
    
    include_inactive: bool = Field(
        default=False,
        description="Include inactive tenants in the dropdown list",
        json_schema_extra={"example": False},
    )
    
    search_term: str | None = Field(
        default=None,
        max_length=100,
        description="Optional search/filter term for tenant names",
        json_schema_extra={"example": "acme"},
    )
    
    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of tenants to return",
        json_schema_extra={"example": 50},
    )


class TenantSearchRequest(WebBFFBaseRequest):
    """
    Request for searching/filtering tenants in the dropdown.
    
    Used for typeahead/autocomplete functionality in Angular.
    """
    
    query: str = Field(
        min_length=1,
        max_length=100,
        description="Search query string",
        json_schema_extra={"example": "acme"},
    )
    
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum results to return",
        json_schema_extra={"example": 10},
    )
    
    include_inactive: bool = Field(
        default=False,
        description="Include inactive tenants in results",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT SELECTION REQUESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TenantSelectionRequest(WebBFFBaseRequest):
    """
    Request when user selects an existing tenant from dropdown.
    
    Either tenant_id or tenant_slug must be provided.
    Used to route user to the tenant's landing page.
    """
    
    tenant_id: UUID | None = Field(
        default=None,
        description="Selected tenant's unique identifier",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    
    tenant_slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$',
        description="Selected tenant's URL-friendly slug",
        json_schema_extra={"example": "acme-corporation"},
    )
    
    @model_validator(mode='after')
    def validate_tenant_identifier(self):
        """Ensure at least one identifier is provided."""
        if not self.tenant_id and not self.tenant_slug:
            raise ValueError(
                "Either 'tenant_id' or 'tenant_slug' must be provided"
            )
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT SIGNUP REQUESTS
# ═══════════════════════════════════════════════════════════════════════════════


class OwnerInfoRequest(WebBFFBaseRequest):
    """Owner's personal information for tenant signup."""
    
    first_name: str = Field(
        min_length=1,
        max_length=100,
        description="Owner's first name",
        json_schema_extra={"example": "John"},
    )
    
    last_name: str = Field(
        min_length=1,
        max_length=100,
        description="Owner's last name",
        json_schema_extra={"example": "Doe"},
    )
    
    email: EmailStr = Field(
        description="Owner's email address (used for login)",
        json_schema_extra={"example": "john.doe@acme.com"},
    )
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name contains only valid characters."""
        if not re.match(r'^[a-zA-Z\s\'\-\.]+$', v):
            raise ValueError(
                'Name can only contain letters, spaces, hyphens, '
                'apostrophes, and periods'
            )
        return v.strip()


class TenantSignupRequest(WebBFFBaseRequest):
    """
    Complete request for new tenant registration.
    
    Contains all information needed to:
    1. Create a new tenant organization
    2. Create the owner/admin user account
    3. Assign tenant_admin role to the owner
    
    This is the main signup form submitted from Angular.
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # Tenant/Business Information
    # ─────────────────────────────────────────────────────────────────────────
    
    business_name: str = Field(
        min_length=2,
        max_length=255,
        description="Name of the business/organization",
        json_schema_extra={"example": "Acme Corporation"},
    )
    
    business_slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$',
        description="URL-friendly identifier (auto-generated if not provided)",
        json_schema_extra={"example": "acme-corporation"},
    )
    
    business_description: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional business description",
        json_schema_extra={"example": "Leading provider of innovative solutions"},
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Owner Information
    # ─────────────────────────────────────────────────────────────────────────
    
    owner_first_name: str = Field(
        min_length=1,
        max_length=100,
        description="Tenant owner's first name",
        json_schema_extra={"example": "John"},
    )
    
    owner_last_name: str = Field(
        min_length=1,
        max_length=100,
        description="Tenant owner's last name",
        json_schema_extra={"example": "Doe"},
    )
    
    owner_email: EmailStr = Field(
        description="Owner's email address (used for account login)",
        json_schema_extra={"example": "john.doe@acme.com"},
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Authentication
    # ─────────────────────────────────────────────────────────────────────────
    
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
        pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$',
        description="Desired username (auto-generated if not provided)",
        json_schema_extra={"example": "johndoe"},
    )
    
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Account password",
        json_schema_extra={"example": "SecureP@ssw0rd!"},
    )
    
    password_confirm: str = Field(
        min_length=8,
        max_length=128,
        description="Password confirmation (must match password)",
        json_schema_extra={"example": "SecureP@ssw0rd!"},
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Optional Contact Information
    # ─────────────────────────────────────────────────────────────────────────
    
    contact_phone: str | None = Field(
        default=None,
        max_length=50,
        description="Business contact phone number",
        json_schema_extra={"example": "+1-555-123-4567"},
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Consent & Terms
    # ─────────────────────────────────────────────────────────────────────────
    
    accept_terms: bool = Field(
        description="User must accept terms of service",
        json_schema_extra={"example": True},
    )
    
    accept_privacy_policy: bool = Field(
        description="User must accept privacy policy",
        json_schema_extra={"example": True},
    )
    
    subscribe_newsletter: bool = Field(
        default=False,
        description="Opt-in to newsletter",
        json_schema_extra={"example": False},
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Validators
    # ─────────────────────────────────────────────────────────────────────────
    
    @field_validator('owner_first_name', 'owner_last_name')
    @classmethod
    def validate_owner_name(cls, v: str) -> str:
        """Validate owner name format."""
        if not re.match(r'^[a-zA-Z\s\'\-\.]+$', v):
            raise ValueError(
                'Name can only contain letters, spaces, hyphens, '
                'apostrophes, and periods'
            )
        return v.strip()
    
    @field_validator('business_name')
    @classmethod
    def validate_business_name(cls, v: str) -> str:
        """Validate and normalize business name."""
        # Remove excessive whitespace
        normalized = ' '.join(v.split())
        
        if len(normalized) < 2:
            raise ValueError('Business name must be at least 2 characters')
        
        return normalized
    
    @field_validator('username', mode='before')
    @classmethod
    def normalize_username(cls, v: str | None) -> str | None:
        """Normalize username to lowercase."""
        if v:
            return v.lower().strip()
        return v
    
    @field_validator('business_slug', mode='before')
    @classmethod
    def normalize_slug(cls, v: str | None) -> str | None:
        """Normalize slug to lowercase."""
        if v:
            return v.lower().strip()
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        errors = []
        
        if not re.search(r'[A-Z]', v):
            errors.append('at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            errors.append('at least one lowercase letter')
        if not re.search(r'\d', v):
            errors.append('at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            errors.append('at least one special character')
        
        if errors:
            raise ValueError(f'Password must contain {", ".join(errors)}')
        
        return v
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        """Ensure password and confirmation match."""
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self
    
    @model_validator(mode='after')
    def validate_terms_accepted(self):
        """Ensure required terms are accepted."""
        if not self.accept_terms:
            raise ValueError('You must accept the terms of service')
        if not self.accept_privacy_policy:
            raise ValueError('You must accept the privacy policy')
        return self
    
    @property
    def owner_full_name(self) -> str:
        """Get owner's full name."""
        return f"{self.owner_first_name} {self.owner_last_name}"


# ═══════════════════════════════════════════════════════════════════════════════
# USERNAME VALIDATION/GENERATION REQUESTS
# ═══════════════════════════════════════════════════════════════════════════════


class UsernameValidationRequest(WebBFFBaseRequest):
    """
    Request to validate if a username is available.
    
    Used for real-time validation in Angular form as user types.
    """
    
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$',
        description="Username to validate",
        json_schema_extra={"example": "johndoe"},
    )
    
    tenant_id: UUID | None = Field(
        default=None,
        description="Tenant context (for checking uniqueness within tenant)",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    
    @field_validator('username', mode='before')
    @classmethod
    def normalize_username(cls, v: str) -> str:
        """Normalize username to lowercase."""
        return v.lower().strip() if v else v


class UsernameGenerationRequest(WebBFFBaseRequest):
    """
    Request to generate a username suggestion.
    
    Used when user doesn't want to choose their own username.
    Can optionally be based on their name.
    """
    
    first_name: str | None = Field(
        default=None,
        max_length=100,
        description="Optional first name for username generation",
        json_schema_extra={"example": "John"},
    )
    
    last_name: str | None = Field(
        default=None,
        max_length=100,
        description="Optional last name for username generation",
        json_schema_extra={"example": "Doe"},
    )
    
    tenant_id: UUID | None = Field(
        default=None,
        description="Tenant context for uniqueness check",
    )
    
    count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of username suggestions to generate",
        json_schema_extra={"example": 3},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SLUG VALIDATION REQUEST
# ═══════════════════════════════════════════════════════════════════════════════


class SlugValidationRequest(WebBFFBaseRequest):
    """
    Request to validate if a tenant slug is available.
    
    Used for real-time validation in Angular form.
    """
    
    slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$',
        description="Slug to validate",
        json_schema_extra={"example": "acme-corp"},
    )
    
    @field_validator('slug', mode='before')
    @classmethod
    def normalize_slug(cls, v: str) -> str:
        """Normalize slug to lowercase."""
        return v.lower().strip() if v else v


class SlugGenerationRequest(WebBFFBaseRequest):
    """
    Request to generate a slug from business name.
    
    Used to auto-suggest slug as user types business name.
    """
    
    business_name: str = Field(
        min_length=2,
        max_length=255,
        description="Business name to generate slug from",
        json_schema_extra={"example": "Acme Corporation"},
    )