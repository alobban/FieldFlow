"""
Role repository for role-specific database operations.
"""

from typing import List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role, UserRole, ROLE_TENANT_ADMIN, ROLE_TENANT_USER
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """
    Repository for Role model operations.
    
    Manages role definitions and user-role assignments.
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize with Role model."""
        super().__init__(Role, session)
    
    async def get_by_name(self, name: str) -> Role | None:
        """
        Get role by name.
        
        Args:
            name: Role name
        
        Returns:
            Role instance or None
        """
        query = select(Role).where(Role.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_tenant_admin_role(self) -> Role | None:
        """
        Get the tenant admin role.
        
        Returns:
            Tenant admin role or None
        """
        return await self.get_by_name(ROLE_TENANT_ADMIN)
    
    async def get_tenant_user_role(self) -> Role | None:
        """
        Get the default tenant user role.
        
        Returns:
            Tenant user role or None
        """
        return await self.get_by_name(ROLE_TENANT_USER)
    
    async def get_system_roles(self) -> List[Role]:
        """
        Get all system-defined roles.
        
        Returns:
            List of system roles
        """
        query = (
            select(Role)
            .where(Role.is_system_role == True)
            .order_by(Role.name)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_all_roles(self) -> List[Role]:
        """
        Get all roles.
        
        Returns:
            List of all roles
        """
        query = select(Role).order_by(Role.name)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def assign_role_to_user(
        self,
        user_id: UUID,
        role_id: UUID,
        is_primary: bool = False,
    ) -> UserRole:
        """
        Assign a role to a user.
        
        Args:
            user_id: User UUID
            role_id: Role UUID
            is_primary: Whether this is the user's primary role
        
        Returns:
            Created UserRole instance
        """
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            is_primary=is_primary,
        )
        
        self.session.add(user_role)
        await self.session.flush()
        await self.session.refresh(user_role)
        
        return user_role
    
    async def remove_role_from_user(
        self,
        user_id: UUID,
        role_id: UUID,
    ) -> bool:
        """
        Remove a role from a user.
        
        Args:
            user_id: User UUID
            role_id: Role UUID
        
        Returns:
            True if removed, False if not found
        """
        query = (
            select(UserRole)
            .where(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id,
                )
            )
        )
        
        result = await self.session.execute(query)
        user_role = result.scalar_one_or_none()
        
        if user_role:
            await self.session.delete(user_role)
            await self.session.flush()
            return True
        
        return False
    
    async def get_user_roles(self, user_id: UUID) -> List[UserRole]:
        """
        Get all roles assigned to a user.
        
        Args:
            user_id: User UUID
        
        Returns:
            List of UserRole instances
        """
        query = (
            select(UserRole)
            .where(UserRole.user_id == user_id)
            .options()
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def user_has_role(
        self,
        user_id: UUID,
        role_name: str,
    ) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            user_id: User UUID
            role_name: Role name to check
        
        Returns:
            True if user has role, False otherwise
        """
        query = (
            select(UserRole)
            .join(UserRole.role)
            .where(
                and_(
                    UserRole.user_id == user_id,
                    Role.name == role_name,
                )
            )
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def set_primary_role(
        self,
        user_id: UUID,
        role_id: UUID,
    ) -> bool:
        """
        Set a role as the user's primary role.
        
        Removes primary flag from other roles.
        
        Args:
            user_id: User UUID
            role_id: Role UUID to set as primary
        
        Returns:
            True if successful
        """
        # Remove primary flag from all user's roles
        user_roles = await self.get_user_roles(user_id)
        for ur in user_roles:
            ur.is_primary = (ur.role_id == role_id)
        
        await self.session.flush()
        return True