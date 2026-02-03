"""
Tenant model for multi-tenant architecture
"""

from enum import Enum
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Text, Enum as SQLEnum, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class TenantStatus(str, Enum):
    """Tenant status enumeration."""
    PENDING_SETUP = "pending_setup"
    TRIAL = "trial"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Tenant(Base, UUIDMixin, TimestampMixin):
    """
    Tenant model representing a business/organization.
    
    Each tenant has its own isolated data and users.
    """
    
    __tablename__ = "tenants"
    __table_args__ = (
        Index("ix_tenants_slug", "slug", unique=True),
        Index("ix_tenants_status", "status"),
        Index("ix_tenants_business_name_search", "business_name"),
    )
    
    # Business Information
    business_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Contact Information
    contact_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    contact_phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # Status
    status: Mapped[TenantStatus] = mapped_column(
        SQLEnum(TenantStatus, name="tenant_status", create_type=False),
        default=TenantStatus.PENDING_SETUP,
        nullable=False,
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # Settings (JSON could be used for flexible settings)
    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    
    custom_domain: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
    )
    
    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, business_name='{self.business_name}', slug='{self.slug}')>"