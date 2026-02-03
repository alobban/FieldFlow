"""
Base repository with common CRUD operations.

Provides generic database operations that can be inherited
by specific entity repositories.
"""

from typing import Any, Generic, List, Type, TypeVar
from uuid import UUID

from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import Base

# Type variable for generic model
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository providing common CRUD operations.
    
    Attributes:
        model: SQLAlchemy model class
        session: Async database session
    """
    
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        Initialize repository.
        
        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session
    
    async def get_by_id(
        self,
        id: UUID,
        options: List[Any] | None = None,
    ) -> ModelType | None:
        """
        Get a single record by ID.
        
        Args:
            id: Record UUID
            options: Optional SQLAlchemy loader options (e.g., selectinload)
        
        Returns:
            Model instance or None if not found
        """
        query = select(self.model).where(self.model.id == id)
        
        if options:
            for option in options:
                query = query.options(option)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        options: List[Any] | None = None,
    ) -> List[ModelType]:
        """
        Get all records with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            options: Optional SQLAlchemy loader options
        
        Returns:
            List of model instances
        """
        query = select(self.model).offset(skip).limit(limit)
        
        if options:
            for option in options:
                query = query.options(option)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_field(
        self,
        field_name: str,
        value: Any,
        options: List[Any] | None = None,
    ) -> ModelType | None:
        """
        Get a single record by field value.
        
        Args:
            field_name: Name of the field to filter by
            value: Value to match
            options: Optional SQLAlchemy loader options
        
        Returns:
            Model instance or None if not found
        """
        field = getattr(self.model, field_name, None)
        if field is None:
            raise ValueError(f"Field '{field_name}' does not exist on {self.model.__name__}")
        
        query = select(self.model).where(field == value)
        
        if options:
            for option in options:
                query = query.options(option)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_many_by_field(
        self,
        field_name: str,
        value: Any,
        skip: int = 0,
        limit: int = 100,
        options: List[Any] | None = None,
    ) -> List[ModelType]:
        """
        Get multiple records by field value.
        
        Args:
            field_name: Name of the field to filter by
            value: Value to match
            skip: Number of records to skip
            limit: Maximum number of records to return
            options: Optional SQLAlchemy loader options
        
        Returns:
            List of model instances
        """
        field = getattr(self.model, field_name, None)
        if field is None:
            raise ValueError(f"Field '{field_name}' does not exist on {self.model.__name__}")
        
        query = (
            select(self.model)
            .where(field == value)
            .offset(skip)
            .limit(limit)
        )
        
        if options:
            for option in options:
                query = query.options(option)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create(self, obj_data: dict[str, Any]) -> ModelType:
        """
        Create a new record.
        
        Args:
            obj_data: Dictionary of field values
        
        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        id: UUID,
        obj_data: dict[str, Any],
    ) -> ModelType | None:
        """
        Update a record by ID.
        
        Args:
            id: Record UUID
            obj_data: Dictionary of fields to update
        
        Returns:
            Updated model instance or None if not found
        """
        # Remove None values to avoid overwriting with null
        update_data = {k: v for k, v in obj_data.items() if v is not None}
        
        if not update_data:
            return await self.get_by_id(id)
        
        query = (
            update(self.model)
            .where(self.model.id == id)
            .values(**update_data)
            .returning(self.model)
        )
        
        result = await self.session.execute(query)
        await self.session.flush()
        
        return result.scalar_one_or_none()
    
    async def delete(self, id: UUID) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id: Record UUID
        
        Returns:
            True if deleted, False if not found
        """
        query = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        await self.session.flush()
        
        return result.rowcount > 0
    
    async def exists(self, id: UUID) -> bool:
        """
        Check if a record exists by ID.
        
        Args:
            id: Record UUID
        
        Returns:
            True if exists, False otherwise
        """
        query = select(func.count()).where(self.model.id == id)
        result = await self.session.execute(query)
        count = result.scalar()
        
        return count is not None and count > 0
    
    async def exists_by_field(self, field_name: str, value: Any) -> bool:
        """
        Check if a record exists by field value.
        
        Args:
            field_name: Name of the field to check
            value: Value to match
        
        Returns:
            True if exists, False otherwise
        """
        field = getattr(self.model, field_name, None)
        if field is None:
            raise ValueError(f"Field '{field_name}' does not exist on {self.model.__name__}")
        
        query = select(func.count()).select_from(self.model).where(field == value)
        result = await self.session.execute(query)
        count = result.scalar()
        
        return count is not None and count > 0
    
    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """
        Count records with optional filters.
        
        Args:
            filters: Optional dictionary of field filters
        
        Returns:
            Number of matching records
        """
        query = select(func.count()).select_from(self.model)
        
        if filters:
            conditions = []
            for field_name, value in filters.items():
                field = getattr(self.model, field_name, None)
                if field is not None:
                    conditions.append(field == value)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        result = await self.session.execute(query)
        count = result.scalar()
        
        return count or 0
    
    async def bulk_create(self, objects_data: List[dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records.
        
        Args:
            objects_data: List of dictionaries with field values
        
        Returns:
            List of created model instances
        """
        db_objects = [self.model(**data) for data in objects_data]
        self.session.add_all(db_objects)
        await self.session.flush()
        
        for obj in db_objects:
            await self.session.refresh(obj)
        
        return db_objects