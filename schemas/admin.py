from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, date


# =============================================================================
# Report Type Schemas
# =============================================================================

class ReportTypeCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50, description="Unique code identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    description: Optional[str] = Field(None, description="Optional description")


class ReportTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ReportTypeResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# =============================================================================
# Recipient Schemas
# =============================================================================

class RecipientCreate(BaseModel):
    email: EmailStr
    report_type_code: str = Field(..., description="Report type code to associate with")
    name: Optional[str] = Field(None, max_length=255)
    is_cc: bool = False
    is_bcc: bool = False


class RecipientUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, max_length=255)
    is_cc: Optional[bool] = None
    is_bcc: Optional[bool] = None
    is_active: Optional[bool] = None


class RecipientResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    report_type_id: int
    report_type_code: Optional[str] = None
    is_active: bool
    is_cc: bool
    is_bcc: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# =============================================================================
# File Schemas
# =============================================================================

class FileResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    file_url: str
    file_size: Optional[int]
    mime_type: Optional[str]
    report_type_id: Optional[int]
    report_date: Optional[date]
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# =============================================================================
# Paginated Response Schemas
# =============================================================================

class PaginatedReportTypeResponse(BaseModel):
    items: List[ReportTypeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedRecipientResponse(BaseModel):
    items: List[RecipientResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedFileResponse(BaseModel):
    items: List[FileResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
