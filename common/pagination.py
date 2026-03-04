from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel, Field
from math import ceil

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Input parameters for pagination."""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(5, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Alias for page_size for database queries."""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: List[T]
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    
    class Config:
        from_attributes = True


def create_paginated_response(
    items: List[T],
    total: int,
    page: int,
    page_size: int
) -> dict:
    """
    Create a paginated response dictionary.
    
    Args:
        items: List of items for the current page
        total: Total count of all items
        page: Current page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Dictionary with pagination metadata
    """
    total_pages = ceil(total / page_size) if page_size > 0 else 0
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }
