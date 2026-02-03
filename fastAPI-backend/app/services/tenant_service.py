"""
Tenant service for tenant-related business logic.
"""

from typing import List
from uuid import UUID
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantStatus
from app.repositories.tenant_repository import TenantRepository
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.core.exceptions import (
    TenantNotFoundException,
    DuplicateException,
    ValidationException,
)


class TenantService:
    """
    Service for tenant business operations.
    
    Handles tenant creation, updates, and queries
    with business rule validation.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize service with database session.
        
        Args:
            session: Async database session
        """
        self.session = session
        self.repository = TenantRepository(session)
    
    async def get_by_id(self, tenant_id: UUID) -> Tenant:
        """
        Get tenant by ID.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            Tenant instance
        
        Raises:
            TenantNotFoundException: If tenant not found
        """
        tenant = await self.repository.get_by_id(tenant_id)
        
        if not tenant:
            raise TenantNotFoundException(identifier=str(tenant_id))
        
        return tenant
    
    async def get_by_slug(self, slug: str) -> Tenant:
        """
        Get tenant by slug.
        
        Args:
            slug: URL-friendly identifier
        
        Returns:
            Tenant instance
        
        Raises:
            TenantNotFoundException: If tenant not found
        """
        tenant = await self.repository.get_by_slug(slug)
        
        if not tenant:
            raise TenantNotFoundException(identifier=slug)
        
        return tenant
    
    async def get_by_id_or_slug(self, identifier: str) -> Tenant:
        """
        Get tenant by ID or slug.
        
        Args:
            identifier: UUID string or slug
        
        Returns:
            Tenant instance
        
        Raises:
            TenantNotFoundException: If tenant not found
        """
        # Try to parse as UUID first
        try:
            tenant_id = UUID(identifier)
            return await self.get_by_id(tenant_id)
        except ValueError:
            # Not a UUID, try as slug
            return await self.get_by_slug(identifier)
    
    async def create(self, data: TenantCreate) -> Tenant:
        """
        Create a new tenant.
        
        Args:
            data: Tenant creation data
        
        Returns:
            Created tenant
        
        Raises:
            DuplicateException: If business name or slug exists
        """
        # Check for duplicate business name
        if await self.repository.business_name_exists(data.business_name):
            raise DuplicateException(
                resource="Tenant",
                field="business_name"
            )
        
        # Generate or validate slug
        slug = data.slug or self._generate_slug(data.business_name)
        
        if await self.repository.slug_exists(slug):
            # Generate unique slug
            slug = await self.repository.generate_unique_slug(slug)
        
        # Create tenant
        tenant_data = {
            "business_name": data.business_name,
            "slug": slug,
            "description": data.description,
            "contact_email": data.contact_email,
            "contact_phone": data.contact_phone,
            "status": TenantStatus.PENDING_SETUP,
            "is_active": True,
        }
        
        tenant = await self.repository.create(tenant_data)
        return tenant
    
    async def update(
        self,
        tenant_id: UUID,
        data: TenantUpdate,
    ) -> Tenant:
        """
        Update a tenant.
        
        Args:
            tenant_id: Tenant UUID
            data: Update data
        
        Returns:
            Updated tenant
        
        Raises:
            TenantNotFoundException: If tenant not found
            DuplicateException: If business name exists
        """
        # Verify tenant exists
        tenant = await self.get_by_id(tenant_id)
        
        # Check for duplicate business name if being changed
        if data.business_name and data.business_name != tenant.business_name:
            if await self.repository.business_name_exists(
                data.business_name,
                exclude_id=tenant_id
            ):
                raise DuplicateException(
                    resource="Tenant",
                    field="business_name"
                )
        
        # Update tenant
        update_dict = data.model_dump(exclude_unset=True)
        updated_tenant = await self.repository.update(tenant_id, update_dict)
        
        if not updated_tenant:
            raise TenantNotFoundException(identifier=str(tenant_id))
        
        return updated_tenant
    
    async def delete(self, tenant_id: UUID) -> bool:
        """
        Delete a tenant.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            True if deleted
        
        Raises:
            TenantNotFoundException: If tenant not found
        """
        # Verify tenant exists
        await self.get_by_id(tenant_id)
        
        return await self.repository.delete(tenant_id)
    
    async def get_active_tenants(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Tenant]:
        """
        Get all active tenants.
        
        Args:
            skip: Records to skip
            limit: Maximum records
        
        Returns:
            List of active tenants
        """
        return await self.repository.get_active_tenants(skip, limit)
    
    async def get_tenants_for_dropdown(
        self,
        include_inactive: bool = False,
        search_term: str | None = None,
        limit: int = 50,
    ) -> List[Tenant]:
        """
        Get tenants for dropdown selection.
        
        Args:
            include_inactive: Include inactive tenants
            search_term: Optional search filter
            limit: Maximum results
        
        Returns:
            List of tenants
        """
        return await self.repository.get_tenants_for_dropdown(
            include_inactive=include_inactive,
            search_term=search_term,
            limit=limit,
        )
    
    async def search(
        self,
        query: str,
        include_inactive: bool = False,
        limit: int = 10,
    ) -> List[Tenant]:
        """
        Search tenants.
        
        Args:
            query: Search string
            include_inactive: Include inactive tenants
            limit: Maximum results
        
        Returns:
            List of matching tenants
        """
        return await self.repository.search_tenants(
            query_string=query,
            include_inactive=include_inactive,
            limit=limit,
        )
    
    async def count_active(self) -> int:
        """
        Count active tenants.
        
        Returns:
            Number of active tenants
        """
        return await self.repository.count_active_tenants()
    
    async def validate_slug(
        self,
        slug: str,
        exclude_id: UUID | None = None,
    ) -> dict:
        """
        Validate a tenant slug.
        
        Args:
            slug: Slug to validate
            exclude_id: Tenant ID to exclude from check
        
        Returns:
            Validation result dict
        """
        # Check format
        slug_pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
        is_valid_format = bool(re.match(slug_pattern, slug.lower()))
        
        if not is_valid_format:
            return {
                "is_available": False,
                "is_valid_format": False,
                "message": "Slug must contain only lowercase letters, numbers, and hyphens",
            }
        
        # Check availability
        is_available = not await self.repository.slug_exists(
            slug.lower(),
            exclude_id=exclude_id
        )
        
        return {
            "is_available": is_available,
            "is_valid_format": True,
            "message": "Slug is available" if is_available else "Slug is already taken",
        }
    
    async def generate_slug(self, business_name: str) -> str:
        """
        Generate a unique slug from business name.
        
        Args:
            business_name: Business name
        
        Returns:
            Unique slug
        """
        base_slug = self._generate_slug(business_name)
        return await self.repository.generate_unique_slug(base_slug)
    
    async def activate(self, tenant_id: UUID) -> Tenant:
        """
        Activate a tenant.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            Activated tenant
        """
        tenant = await self.repository.activate(tenant_id)
        
        if not tenant:
            raise TenantNotFoundException(identifier=str(tenant_id))
        
        return tenant
    
    async def deactivate(self, tenant_id: UUID) -> Tenant:
        """
        Deactivate a tenant.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            Deactivated tenant
        """
        tenant = await self.repository.deactivate(tenant_id)
        
        if not tenant:
            raise TenantNotFoundException(identifier=str(tenant_id))
        
        return tenant
    
    async def complete_setup(self, tenant_id: UUID) -> Tenant:
        """
        Mark tenant setup as complete.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            Updated tenant
        """
        return await self.repository.update_status(
            tenant_id,
            TenantStatus.ACTIVE
        )
    
    def _generate_slug(self, business_name: str) -> str:
        """
        Generate slug from business name.
        
        Args:
            business_name: Business name
        
        Returns:
            Generated slug
        """
        # Convert to lowercase
        slug = business_name.lower()
        
        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        # Remove consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        
        return slug