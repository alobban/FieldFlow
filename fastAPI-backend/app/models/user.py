"""
User model for authentication and tenant membership
"""

from enum import Enum
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import String, Boolean, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.role import UserRole


class UserStatus(str, Enum):
    """User status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Base, UUIDMixin, TimestampMixin):
    """
    User model for authentication and tenant membership.
    
    Users belong to a specific tenant and have roles within that tenant.
    """
    
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_tenant_username", "tenant_id", "username", unique=True),
        Index("ix_users_tenant_email", "tenant_id", "email", unique=True),
        Index("ix_users_status", "status"),
    )
    
    # Tenant Association
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Authentication
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # Profile Information
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    # Status
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus, name="user_status", create_type=False),
        default=UserStatus.PENDING,
        nullable=False,
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    is_tenant_owner: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="users",
        lazy="joined",
    )
    
    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def role_names(self) -> List[str]:
        """Get list of role names for this user."""
        return [ur.role.name for ur in self.user_roles if ur.role]
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', tenant_id={self.tenant_id})>"