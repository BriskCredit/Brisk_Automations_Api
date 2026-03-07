from pydantic import BaseModel
from typing import List, TypeVar, Generic

T = TypeVar('T')


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    success: bool = True


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
