"""
Repository layer for data access.

Repositories handle all database operations and provide
a clean abstraction over SQLAlchemy queries.
"""

from app.repositories.base import BaseRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository

__all__ = [
    "BaseRepository",
    "TenantRepository",
    "UserRepository",
    "RoleRepository",
]