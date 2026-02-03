"""
Authentication API endpoints.

Provides endpoints for user authentication within tenant context.
"""

from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, EmailStr, ConfigDict

from app.database import get_db_session
from app.services.user_service import UserService
from app.services.tenant_service import TenantService
from app.core.security import create_access_token, decode_access_token
from app.core.dependencies import RequiredTenant
from app.core.exceptions import UserNotFoundException, TenantNotFoundException
from app.config import settings

router = APIRouter()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class TokenResponse(BaseModel):
    """Token response schema."""
    
    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration in seconds")
    user_id: UUID = Field(description="Authenticated user ID")
    tenant_id: UUID = Field(description="User's tenant ID")
    username: str = Field(description="User's username")
    roles: list[str] = Field(description="User's roles")


class LoginRequest(BaseModel):
    """Login request schema."""
    
    username_or_email: str = Field(
        min_length=3,
        description="Username or email address",
    )
    password: str = Field(
        min_length=1,
        description="User's password",
    )
    tenant_id: UUID | None = Field(
        default=None,
        description="Tenant ID (alternative to header)",
    )


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    
    refresh_token: str = Field(description="Refresh token")


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""
    
    current_password: str = Field(
        min_length=1,
        description="Current password",
    )
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="New password",
    )


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    
    email: EmailStr = Field(description="User's email address")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""
    
    token: str = Field(description="Password reset token")
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="New password",
    )


class UserInfoResponse(BaseModel):
    """Current user info response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(description="User ID")
    tenant_id: UUID = Field(description="Tenant ID")
    username: str = Field(description="Username")
    email: str = Field(description="Email address")
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    full_name: str = Field(description="Full name")
    is_active: bool = Field(description="Whether user is active")
    is_tenant_owner: bool = Field(description="Whether user is tenant owner")
    email_verified: bool = Field(description="Whether email is verified")
    roles: list[str] = Field(description="User's roles")


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Get Access Token (OAuth2)",
    description="Authenticate with username/email and password using OAuth2 form.",
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    tenant_id: RequiredTenant,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    OAuth2 compatible token login.
    
    Requires X-Tenant-ID header or tenantId query parameter.
    """
    user_service = UserService(session)
    
    # Authenticate user
    user = await user_service.authenticate(
        username_or_email=form_data.username,
        password=form_data.password,
        tenant_id=tenant_id,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    expires_in = 60 * 60 * 24  # 24 hours
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "username": user.username,
            "roles": [ur.role.name for ur in user.user_roles] if user.user_roles else [],
        },
        expires_delta=timedelta(seconds=expires_in),
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user_id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        roles=[ur.role.name for ur in user.user_roles] if user.user_roles else [],
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate with username/email and password.",
)
async def login(
    request: LoginRequest,
    tenant_id: Annotated[UUID | None, Depends(lambda: None)] = None,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Login endpoint for JSON requests.
    
    Tenant ID can be provided in:
    - Request body (tenant_id field)
    - X-Tenant-ID header
    - tenantId query parameter
    """
    user_service = UserService(session)
    
    # Determine tenant ID
    effective_tenant_id = request.tenant_id or tenant_id
    if not effective_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID is required (provide in body, header, or query)",
        )
    
    # Authenticate user
    user = await user_service.authenticate(
        username_or_email=request.username_or_email,
        password=request.password,
        tenant_id=effective_tenant_id,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )
    
    # Create access token
    expires_in = 60 * 60 * 24  # 24 hours
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "username": user.username,
            "roles": [ur.role.name for ur in user.user_roles] if user.user_roles else [],
        },
        expires_delta=timedelta(seconds=expires_in),
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user_id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        roles=[ur.role.name for ur in user.user_roles] if user.user_roles else [],
    )


@router.get(
    "/me",
    response_model=UserInfoResponse,
    summary="Get Current User",
    description="Get information about the currently authenticated user.",
)
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_db_session),
) -> UserInfoResponse:
    """
    Get current authenticated user's information.
    """
    # Decode token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # Get user
    user_service = UserService(session)
    
    try:
        user = await user_service.get_by_id(UUID(user_id))
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserInfoResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=f"{user.first_name} {user.last_name}",
        is_active=user.is_active,
        is_tenant_owner=user.is_tenant_owner,
        email_verified=user.email_verified,
        roles=[ur.role.name for ur in user.user_roles] if user.user_roles else [],
    )


@router.post(
    "/verify-token",
    summary="Verify Token",
    description="Verify if a token is valid.",
)
async def verify_token(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict:
    """
    Verify if a token is valid and not expired.
    """
    payload = decode_access_token(token)
    
    if not payload:
        return {
            "valid": False,
            "message": "Invalid or expired token",
        }
    
    return {
        "valid": True,
        "user_id": payload.get("sub"),
        "tenant_id": payload.get("tenant_id"),
        "username": payload.get("username"),
        "roles": payload.get("roles", []),
    }


@router.post(
    "/change-password",
    summary="Change Password",
    description="Change the current user's password.",
)
async def change_password(
    request: PasswordChangeRequest,
    token: Annotated[str, Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Change the current user's password.
    
    Requires current password for verification.
    """
    # Decode token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    user_id = UUID(payload.get("sub"))
    tenant_id = UUID(payload.get("tenant_id"))
    
    user_service = UserService(session)
    
    # Verify current password
    user = await user_service.authenticate(
        username_or_email=payload.get("username"),
        password=request.current_password,
        tenant_id=tenant_id,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    # Update password
    from app.core.security import hash_password
    await user_service.user_repository.update(
        user_id,
        {"password_hash": hash_password(request.new_password)},
    )
    
    return {
        "message": "Password changed successfully",
        "success": True,
    }


@router.post(
    "/logout",
    summary="Logout",
    description="Logout the current user (client should discard token).",
)
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict:
    """
    Logout endpoint.
    
    Note: With JWT tokens, logout is typically handled client-side
    by discarding the token. This endpoint is provided for
    API completeness and could be used for token blacklisting
    in a production implementation.
    """
    # In a production app, you might want to:
    # 1. Add the token to a blacklist (Redis, database, etc.)
    # 2. Invalidate any refresh tokens
    
    return {
        "message": "Successfully logged out",
        "success": True,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PASSWORD RESET ENDPOINTS (Placeholder implementations)
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/password-reset/request",
    summary="Request Password Reset",
    description="Request a password reset email.",
)
async def request_password_reset(
    request: PasswordResetRequest,
    tenant_id: RequiredTenant,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Request a password reset.
    
    Sends a password reset email to the user if the email exists.
    Always returns success to prevent email enumeration.
    """
    # In a production app:
    # 1. Look up user by email in tenant
    # 2. Generate a secure reset token
    # 3. Store the token with expiration
    # 4. Send reset email
    
    # Always return success to prevent email enumeration
    return {
        "message": "If an account exists with this email, a reset link has been sent.",
        "success": True,
    }


@router.post(
    "/password-reset/confirm",
    summary="Confirm Password Reset",
    description="Reset password using reset token.",
)
async def confirm_password_reset(
    request: PasswordResetConfirm,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Confirm password reset with token.
    
    This is a placeholder implementation.
    In production, you would:
    1. Validate the reset token
    2. Check token expiration
    3. Update the user's password
    4. Invalidate the token
    """
    # Placeholder - implement token validation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset confirmation not yet implemented",
    )