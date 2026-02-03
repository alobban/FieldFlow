"""
BFF-specific schemas for Web (Angular) frontend.

These schemas are tailored for the Angular frontend's needs,
providing optimized data structures for specific UI views.
"""

from app.schemas.bff.web_requests import (
    LandingPageRequest,
    TenantSignupRequest,
    TenantSelectionRequest,
    UsernameValidationRequest,
    UsernameGenerationRequest,
    TenantSearchRequest,
)
from app.schemas.bff.web_responses import (
    LandingPageResponse,
    TenantDropdownItem,
    TenantSignupResponse,
    TenantLandingPageResponse,
    UsernameValidationResponse,
    UsernameGenerationResponse,
    OnboardingStatusResponse,
    TenantRouteInfo,
    SignupFormConfig,
    FieldValidationError,
    SignupValidationResponse,
)

__all__ = [
    # Requests
    "LandingPageRequest",
    "TenantSignupRequest",
    "TenantSelectionRequest",
    "UsernameValidationRequest",
    "UsernameGenerationRequest",
    "TenantSearchRequest",
    # Responses
    "LandingPageResponse",
    "TenantDropdownItem",
    "TenantSignupResponse",
    "TenantLandingPageResponse",
    "UsernameValidationResponse",
    "UsernameGenerationResponse",
    "OnboardingStatusResponse",
    "TenantRouteInfo",
    "SignupFormConfig",
    "FieldValidationError",
    "SignupValidationResponse",
]