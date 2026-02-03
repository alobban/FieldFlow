"""
User repository for user-specific database operations.
"""

from typing import List
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.user import User, UserStatus
from app.models.role import UserRole, Role
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Repository for User model operations.
    
    Provides specialized queries for user management
    within tenant context.
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize with User model."""
        super().__init__(User, session)
    
    async def get_by_username(
        self,
        username: str,
        tenant_id: UUID,
    ) -> User | None:
        """
        Get user by username within a tenant.
        
        Args:
            username: User's username
            tenant_id: Tenant UUID
        
        Returns:
            User instance or None
        """
        query = (
            select(User)
            .where(
                and_(
                    func.lower(User.username) == username.lower(),
                    User.tenant_id == tenant_id,
                )
            )
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_email(
        self,
        email: str,
        tenant_id: UUID,
    ) -> User | None:
        """
        Get user by email within a tenant.
        
        Args:
            email: User's email address
            tenant_id: Tenant UUID
        
        Returns:
            User instance or None
        """
        query = (
            select(User)
            .where(
                and_(
                    func.lower(User.email) == email.lower(),
                    User.tenant_id == tenant_id,
                )
            )
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_email_any_tenant(self, email: str) -> User | None:
        """
        Get user by email across all tenants.
        
        Used for checking global email uniqueness if required.
        
        Args:
            email: User's email address
        
        Returns:
            User instance or None
        """
        query = (
            select(User)
            .where(func.lower(User.email) == email.lower())
            .limit(1)
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_tenant_users(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> List[User]:
        """
        Get all users for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            skip: Number of records to skip
            limit: Maximum records to return
            include_inactive: Include inactive users
        
        Returns:
            List of users
        """
        conditions = [User.tenant_id == tenant_id]
        
        if not include_inactive:
            conditions.append(User.is_active == True)
        
        query = (
            select(User)
            .where(and_(*conditions))
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .order_by(User.last_name, User.first_name)
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_tenant_owner(self, tenant_id: UUID) -> User | None:
        """
        Get the owner user for a tenant.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            Owner user or None
        """
        query = (
            select(User)
            .where(
                and_(
                    User.tenant_id == tenant_id,
                    User.is_tenant_owner == True,
                )
            )
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_users_by_role(
        self,
        tenant_id: UUID,
        role_name: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """
        Get users with a specific role.
        
        Args:
            tenant_id: Tenant UUID
            role_name: Role name to filter by
            skip: Number of records to skip
            limit: Maximum records to return
        
        Returns:
            List of users with the role
        """
        query = (
            select(User)
            .join(User.user_roles)
            .join(UserRole.role)
            .where(
                and_(
                    User.tenant_id == tenant_id,
                    User.is_active == True,
                    Role.name == role_name,
                )
            )
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .order_by(User.last_name, User.first_name)
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def username_exists(
        self,
        username: str,
        tenant_id: UUID,
        exclude_id: UUID | None = None,
    ) -> bool:
        """
        Check if username exists within a tenant.
        
        Args:
            username: Username to check
            tenant_id: Tenant UUID
            exclude_id: Optional user ID to exclude
        
        Returns:
            True if username exists, False otherwise
        """
        conditions = [
            func.lower(User.username) == username.lower(),
            User.tenant_id == tenant_id,
        ]
        
        if exclude_id:
            conditions.append(User.id != exclude_id)
        
        query = (
            select(func.count())
            .select_from(User)
            .where(and_(*conditions))
        )
        
        result = await self.session.execute(query)
        count = result.scalar()
        
        return count is not None and count > 0
    
    async def email_exists(
        self,
        email: str,
        tenant_id: UUID,
        exclude_id: UUID | None = None,
    ) -> bool:
        """
        Check if email exists within a tenant.
        
        Args:
            email: Email to check
            tenant_id: Tenant UUID
            exclude_id: Optional user ID to exclude
        
        Returns:
            True if email exists, False otherwise
        """
        conditions = [
            func.lower(User.email) == email.lower(),
            User.tenant_id == tenant_id,
        ]
        
        if exclude_id:
            conditions.append(User.id != exclude_id)
        
        query = (
            select(func.count())
            .select_from(User)
            .where(and_(*conditions))
        )
        
        result = await self.session.execute(query)
        count = result.scalar()
        
        return count is not None and count > 0
    
    async def search_users(
        self,
        tenant_id: UUID,
        query_string: str,
        limit: int = 10,
    ) -> List[User]:
        """
        Search users by name, username, or email.
        
        Args:
            tenant_id: Tenant UUID
            query_string: Search query
            limit: Maximum results
        
        Returns:
            List of matching users
        """
        search_pattern = f"%{query_string.lower()}%"
        
        query = (
            select(User)
            .where(
                and_(
                    User.tenant_id == tenant_id,
                    User.is_active == True,
                    or_(
                        func.lower(User.username).like(search_pattern),
                        func.lower(User.email).like(search_pattern),
                        func.lower(User.first_name).like(search_pattern),
                        func.lower(User.last_name).like(search_pattern),
                        func.concat(
                            func.lower(User.first_name),
                            ' ',
                            func.lower(User.last_name)
                        ).like(search_pattern),
                    )
                )
            )
            .order_by(User.last_name, User.first_name)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def count_tenant_users(
        self,
        tenant_id: UUID,
        include_inactive: bool = False,
    ) -> int:
        """
        Count users in a tenant.
        
        Args:
            tenant_id: Tenant UUID
            include_inactive: Include inactive users
        
        Returns:
            User count
        """
        conditions = [User.tenant_id == tenant_id]
        
        if not include_inactive:
            conditions.append(User.is_active == True)
        
        query = (
            select(func.count())
            .select_from(User)
            .where(and_(*conditions))
        )
        
        result = await self.session.execute(query)
        count = result.scalar()
        
        return count or 0
    
    async def get_with_roles(self, user_id: UUID) -> User | None:
        """
        Get user with eagerly loaded roles.
        
        Args:
            user_id: User UUID
        
        Returns:
            User with roles loaded or None
        """
        query = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.user_roles).selectinload(UserRole.role),
                joinedload(User.tenant),
            )
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update_status(
        self,
        user_id: UUID,
        status: UserStatus,
    ) -> User | None:
        """
        Update user status.
        
        Args:
            user_id: User UUID
            status: New status
        
        Returns:
            Updated user or None
        """
        return await self.update(user_id, {"status": status})
    
    async def verify_email(self, user_id: UUID) -> User | None:
        """
        Mark user's email as verified.
        
        Args:
            user_id: User UUID
        
        Returns:
            Updated user or None
        """
        return await self.update(
            user_id,
            {
                "email_verified": True,
                "status": UserStatus.ACTIVE,
            }
        )
    
    async def deactivate(self, user_id: UUID) -> User | None:
        """
        Deactivate a user.
        
        Args:
            user_id: User UUID
        
        Returns:
            Updated user or None
        """
        return await self.update(
            user_id,
            {
                "is_active": False,
                "status": UserStatus.INACTIVE,
            }
        )
    
    async def generate_unique_username(
        self,
        base_username: str,
        tenant_id: UUID,
    ) -> str:
        """
        Generate a unique username within a tenant.
        
        Args:
            base_username: Base username to make unique
            tenant_id: Tenant UUID
        
        Returns:
            Unique username string
        """
        username = base_username.lower()
        
        if not await self.username_exists(username, tenant_id):
            return username
        
        # Find existing usernames with this base
        pattern = f"{username}%"
        query = (
            select(User.username)
            .where(
                and_(
                    User.tenant_id == tenant_id,
                    func.lower(User.username).like(pattern),
                )
            )
        )
        
        result = await self.session.execute(query)
        existing_usernames = {u.lower() for u in result.scalars().all()}
        
        # Find next available number
        counter = 1
        while True:
            new_username = f"{username}{counter}"
            if new_username not in existing_usernames:
                return new_username
            counter += 1