"""
Tenant-related Pydantic schemas
"""

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import Field, field_validator
import re

from app.schemas.base import BaseSchema, IDTimestampSchema
from app.models.tenant import TenantStatus


class TenantBase(BaseSchema):
    """Base tenant schema with common fields."""
    
    business_name: str = Field(
        min_length=2,
        max_length=255,
        description="Name of the business/tenant"
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Tenant description"
    )
    contact_email: str | None = Field(
        default=None,
        max_length=255,
        description="Contact email address"
    )
    contact_phone: str | None = Field(
        default=None,
        max_length=50,
        description="Contact phone number"
    )


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""
    
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$',
        description="URL-friendly identifier (auto-generated if not provided)"
    )
    
    @field_validator('slug', mode='before')
    @classmethod
    def generate_slug(cls, v: str | None, info) -> str | None:
        if v:
            # Ensure slug is lowercase and valid
            return v.lower().strip()
        return v


class TenantUpdate(BaseSchema):
    """Schema for updating a tenant."""
    
    business_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    contact_email: str | None = Field(
        default=None,
        max_length=255,
    )
    contact_phone: str | None = Field(
        default=None,
        max_length=50,
    )
    logo_url: str | None = Field(
        default=None,
        max_length=500,
    )
    status: TenantStatus | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class TenantResponse(IDTimestampSchema, TenantBase):
    """Full tenant response schema."""
    
    slug: str = Field(description="URL-friendly identifier")
    status: TenantStatus = Field(description="Tenant status")
    is_active: bool = Field(description="Whether tenant is active")
    logo_url: str | None = Field(default=None, description="Logo URL")
    custom_domain: str | None = Field(default=None, description="Custom domain")


class TenantListItem(BaseSchema):
    """Minimal tenant info for dropdown lists."""
    
    id: UUID = Field(description="Tenant ID")
    business_name: str = Field(description="Business name")
    slug: str = Field(description="URL slug")
    logo_url: str | None = Field(default=None, description="Logo URL")
    is_active: bool = Field(description="Whether tenant is active")


class TenantPublicInfo(BaseSchema):
    """Public tenant information (no sensitive data)."""
    
    id: UUID = Field(description="Tenant ID")
    business_name: str = Field(description="Business name")
    slug: str = Field(description="URL slug")
    description: str | None = Field(default=None)
    logo_url: str | None = Field(default=None)