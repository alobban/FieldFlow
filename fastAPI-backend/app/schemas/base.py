"""
Base Pydantic schemas and common types
"""

from datetime import datetime
from typing import Generic, TypeVar, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        },
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class IDSchema(BaseSchema):
    """Schema with ID field."""
    
    id: UUID = Field(description="Unique identifier")


class IDTimestampSchema(IDSchema, TimestampSchema):
    """Schema with ID and timestamp fields."""
    pass


# Generic type for paginated responses
T = TypeVar("T")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response schema."""
    
    items: List[T] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number", ge=1)
    page_size: int = Field(description="Number of items per page", ge=1, le=100)
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")


class MessageResponse(BaseSchema):
    """Simple message response."""
    
    message: str = Field(description="Response message")
    success: bool = Field(default=True, description="Operation success status")


class ErrorResponse(BaseSchema):
    """Error response schema."""
    
    detail: str = Field(description="Error detail message")
    error_code: str | None = Field(default=None, description="Error code")