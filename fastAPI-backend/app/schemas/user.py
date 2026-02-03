"""
User-related Pydantic schemas
"""

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import Field, EmailStr, field_validator
import re

from app.schemas.base import BaseSchema, IDTimestampSchema
from app.models.user import UserStatus


class UserBase(BaseSchema):
    """Base user schema with common fields."""
    
    first_name: str = Field(
        min_length=1,
        max_length=100,
        description="User's first name"
    )
    last_name: str = Field(
        min_length=1,
        max_length=100,
        description="User's last name"
    )
    email: EmailStr = Field(description="User's email address")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
        pattern=r'^[a-zA-Z0-9_]+$',
        description="Username (auto-generated if not provided)"
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="User password"
    )
    
    @field_validator('username', mode='before')
    @classmethod
    def normalize_username(cls, v: str | None) -> str | None:
        if v:
            return v.lower().strip()
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseSchema):
    """Schema for updating a user."""
    
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = Field(default=None)
    status: UserStatus | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class UserRoleInfo(BaseSchema):
    """User role information."""
    
    role_id: UUID = Field(description="Role ID")
    role_name: str = Field(description="Role name")
    display_name: str = Field(description="Role display name")
    is_primary: bool = Field(description="Whether this is the primary role")


class UserResponse(IDTimestampSchema, UserBase):
    """Full user response schema."""
    
    tenant_id: UUID = Field(description="Associated tenant ID")
    username: str = Field(description="Username")
    status: UserStatus = Field(description="User status")
    is_active: bool = Field(description="Whether user is active")
    is_tenant_owner: bool = Field(description="Whether user is tenant owner")
    email_verified: bool = Field(description="Whether email is verified")
    roles: List[str] = Field(default_factory=list, description="User role names")
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class UserListItem(BaseSchema):
    """Minimal user info for lists."""
    
    id: UUID = Field(description="User ID")
    username: str = Field(description="Username")
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    email: str = Field(description="Email")
    is_active: bool = Field(description="Whether user is active")
    is_tenant_owner: bool = Field(description="Whether user is tenant owner")