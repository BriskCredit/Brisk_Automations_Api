from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime


class RunRequest(BaseModel):
    """Request body for manual run."""
    override_recipients: Optional[List[EmailStr]] = None


class RunResponse(BaseModel):
    """Response for manual run."""
    success: bool
    message: str
    rows: Optional[int] = None
    file_path: Optional[str] = None


class StatusResponse(BaseModel):
    """Status of a report type."""
    report_type_code: str
    report_type_name: str
    is_active: bool
    recipient_count: int
    recipients: List[dict]


class PreviewResponse(BaseModel):
    """Response for preview endpoint."""
    success: bool
    generated_at: datetime
    row_count: int
    columns: List[str]
    summary: List[dict]


class PreviewSummary(BaseModel):
    """Summary of preview data."""
    branch: str
    d7: Optional[str] = None
    d30: Optional[str] = None
    dd_30: Optional[str] = None
    dd_60: Optional[str] = None
