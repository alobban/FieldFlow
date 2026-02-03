"""
Tenant repository for tenant-specific database operations.
"""

from typing import List
from uuid import UUID
import re

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tenant import Tenant, TenantStatus
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    """
    Repository for Tenant model operations.
    
    Provides specialized queries for tenant management.
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize with Tenant model."""
        super().__init__(Tenant, session)
    
    async def get_by_slug(self, slug: str) -> Tenant | None:
        """
        Get tenant by URL slug.
        
        Args:
            slug: URL-friendly tenant identifier
        
        Returns:
            Tenant instance or None
        """
        query = select(Tenant).where(Tenant.slug == slug.lower())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_business_name(self, business_name: str) -> Tenant | None:
        """
        Get tenant by exact business name.
        
        Args:
            business_name: Business name to search
        
        Returns:
            Tenant instance or None
        """
        query = select(Tenant).where(
            func.lower(Tenant.business_name) == business_name.lower()
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_tenants(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Tenant]:
        """
        Get all active tenants.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
        
        Returns:
            List of active tenants
        """
        query = (
            select(Tenant)
            .where(
                and_(
                    Tenant.is_active == True,
                    Tenant.status.in_([
                        TenantStatus.ACTIVE,
                        TenantStatus.TRIAL,
                    ])
                )
            )
            .order_by(Tenant.business_name)
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_tenants_for_dropdown(
        self,
        include_inactive: bool = False,
        search_term: str | None = None,
        limit: int = 50,
    ) -> List[Tenant]:
        """
        Get tenants optimized for dropdown selection.
        
        Args:
            include_inactive: Include inactive tenants
            search_term: Optional search filter
            limit: Maximum results
        
        Returns:
            List of tenants for dropdown
        """
        conditions = []
        
        if not include_inactive:
            conditions.append(Tenant.is_active == True)
            conditions.append(
                Tenant.status.in_([
                    TenantStatus.ACTIVE,
                    TenantStatus.TRIAL,
                    TenantStatus.PENDING_SETUP,
                ])
            )
        
        if search_term:
            search_pattern = f"%{search_term.lower()}%"
            conditions.append(
                or_(
                    func.lower(Tenant.business_name).like(search_pattern),
                    func.lower(Tenant.slug).like(search_pattern),
                )
            )
        
        query = (
            select(Tenant)
            .where(and_(*conditions) if conditions else True)
            .order_by(Tenant.business_name)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def search_tenants(
        self,
        query_string: str,
        include_inactive: bool = False,
        limit: int = 10,
    ) -> List[Tenant]:
        """
        Search tenants by name or slug.
        
        Args:
            query_string: Search query
            include_inactive: Include inactive tenants
            limit: Maximum results
        
        Returns:
            List of matching tenants
        """
        search_pattern = f"%{query_string.lower()}%"
        
        conditions = [
            or_(
                func.lower(Tenant.business_name).like(search_pattern),
                func.lower(Tenant.slug).like(search_pattern),
                func.lower(Tenant.description).like(search_pattern),
            )
        ]
        
        if not include_inactive:
            conditions.append(Tenant.is_active == True)
        
        query = (
            select(Tenant)
            .where(and_(*conditions))
            .order_by(Tenant.business_name)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def slug_exists(self, slug: str, exclude_id: UUID | None = None) -> bool:
        """
        Check if a slug already exists.
        
        Args:
            slug: Slug to check
            exclude_id: Optional tenant ID to exclude (for updates)
        
        Returns:
            True if slug exists, False otherwise
        """
        conditions = [Tenant.slug == slug.lower()]
        
        if exclude_id:
            conditions.append(Tenant.id != exclude_id)
        
        query = (
            select(func.count())
            .select_from(Tenant)
            .where(and_(*conditions))
        )
        
        result = await self.session.execute(query)
        count = result.scalar()
        
        return count is not None and count > 0
    
    async def business_name_exists(
        self,
        business_name: str,
        exclude_id: UUID | None = None,
    ) -> bool:
        """
        Check if a business name already exists.
        
        Args:
            business_name: Business name to check
            exclude_id: Optional tenant ID to exclude
        
        Returns:
            True if name exists, False otherwise
        """
        conditions = [func.lower(Tenant.business_name) == business_name.lower()]
        
        if exclude_id:
            conditions.append(Tenant.id != exclude_id)
        
        query = (
            select(func.count())
            .select_from(Tenant)
            .where(and_(*conditions))
        )
        
        result = await self.session.execute(query)
        count = result.scalar()
        
        return count is not None and count > 0
    
    async def get_with_users(self, tenant_id: UUID) -> Tenant | None:
        """
        Get tenant with eagerly loaded users.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            Tenant with users loaded or None
        """
        query = (
            select(Tenant)
            .where(Tenant.id == tenant_id)
            .options(selectinload(Tenant.users))
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def count_active_tenants(self) -> int:
        """
        Count all active tenants.
        
        Returns:
            Number of active tenants
        """
        query = (
            select(func.count())
            .select_from(Tenant)
            .where(
                and_(
                    Tenant.is_active == True,
                    Tenant.status.in_([
                        TenantStatus.ACTIVE,
                        TenantStatus.TRIAL,
                        TenantStatus.PENDING_SETUP,
                    ])
                )
            )
        )
        
        result = await self.session.execute(query)
        count = result.scalar()
        
        return count or 0
    
    async def generate_unique_slug(self, base_slug: str) -> str:
        """
        Generate a unique slug based on a base value.
        
        If base_slug exists, appends numbers until unique.
        
        Args:
            base_slug: Base slug to make unique
        
        Returns:
            Unique slug string
        """
        # Normalize the base slug
        slug = re.sub(r'[^a-z0-9]+', '-', base_slug.lower())
        slug = slug.strip('-')
        
        if not await self.slug_exists(slug):
            return slug
        
        # Find existing slugs with this base
        pattern = f"{slug}%"
        query = (
            select(Tenant.slug)
            .where(Tenant.slug.like(pattern))
        )
        
        result = await self.session.execute(query)
        existing_slugs = set(result.scalars().all())
        
        # Find next available number
        counter = 1
        while True:
            new_slug = f"{slug}-{counter}"
            if new_slug not in existing_slugs:
                return new_slug
            counter += 1
    
    async def update_status(
        self,
        tenant_id: UUID,
        status: TenantStatus,
    ) -> Tenant | None:
        """
        Update tenant status.
        
        Args:
            tenant_id: Tenant UUID
            status: New status
        
        Returns:
            Updated tenant or None
        """
        return await self.update(tenant_id, {"status": status})
    
    async def deactivate(self, tenant_id: UUID) -> Tenant | None:
        """
        Deactivate a tenant.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            Updated tenant or None
        """
        return await self.update(
            tenant_id,
            {
                "is_active": False,
                "status": TenantStatus.INACTIVE,
            }
        )
    
    async def activate(self, tenant_id: UUID) -> Tenant | None:
        """
        Activate a tenant.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            Updated tenant or None
        """
        return await self.update(
            tenant_id,
            {
                "is_active": True,
                "status": TenantStatus.ACTIVE,
            }
        )