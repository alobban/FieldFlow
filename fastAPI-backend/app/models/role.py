"""
Role and UserRole models for RBAC
"""

from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import String, Text, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Role(Base, UUIDMixin, TimestampMixin):
    """
    Role model for role-based access control.
    
    Defines available roles in the system.
    """
    
    __tablename__ = "roles"
    __table_args__ = (
        Index("ix_roles_name", "name", unique=True),
    )
    
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )
    
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    is_system_role: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # Relationships
    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}')>"


# System role constants
ROLE_TENANT_ADMIN = "tenant_admin"
ROLE_TENANT_USER = "tenant_user"
ROLE_TENANT_VIEWER = "tenant_viewer"


class UserRole(Base, UUIDMixin, TimestampMixin):
    """
    Association model between User and Role.
    
    Links users to their roles within a tenant.
    """
    
    __tablename__ = "user_roles"
    __table_args__ = (
        Index("ix_user_roles_user_role", "user_id", "role_id", unique=True),
    )
    
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_roles",
        lazy="joined",
    )
    
    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="user_roles",
        lazy="joined",
    )
    
    def __repr__(self) -> str:
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"