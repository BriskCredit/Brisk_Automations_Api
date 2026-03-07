from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime


# =============================================================================
# Job Schemas
# =============================================================================

class JobCreate(BaseModel):
    """Schema for creating a new job."""
    title: str = Field(..., min_length=1, max_length=255)
    summary: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    qualifications: Optional[str] = None
    benefits: Optional[str] = None
    notes: Optional[str] = Field(None, description="Internal notes (not shown to applicants)")
    custom_instructions: Optional[str] = Field(None, description="AI instructions for CV analysis (priority)")
    location: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=100)
    employment_type: Optional[str] = Field(None, max_length=50)
    expires_at: Optional[datetime] = Field(None, description="Expiry date for the job posting")
    publish: bool = Field(False, description="If true, publish the job immediately after creation")


class JobUpdate(BaseModel):
    """Schema for updating a job."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    summary: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    qualifications: Optional[str] = None
    benefits: Optional[str] = None
    notes: Optional[str] = None
    custom_instructions: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    employment_type: Optional[str] = None
    expires_at: Optional[datetime] = None


class JobResponse(BaseModel):
    """Response schema for a job."""
    id: int
    title: str
    summary: Optional[str]
    responsibilities: Optional[str]
    requirements: Optional[str]
    qualifications: Optional[str]
    benefits: Optional[str]
    notes: Optional[str]
    custom_instructions: Optional[str]
    status: str
    location: Optional[str]
    department: Optional[str]
    employment_type: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    published_at: Optional[datetime]
    closed_at: Optional[datetime]
    expires_at: Optional[datetime] = None
    is_expired: bool = False
    application_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Paginated response for job list."""
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PublicJobResponse(BaseModel):
    """Public response schema for a job (excludes admin-only fields)."""
    id: int
    title: str
    summary: Optional[str]
    responsibilities: Optional[str]
    requirements: Optional[str]
    qualifications: Optional[str]
    benefits: Optional[str]
    location: Optional[str]
    department: Optional[str]
    employment_type: Optional[str]
    published_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class PublicJobListResponse(BaseModel):
    """Paginated response for public job list."""
    items: List[PublicJobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# =============================================================================
# Application Schemas
# =============================================================================

class ApplicationResponse(BaseModel):
    """Response schema for a job application."""
    id: int
    job_id: int
    applicant_name: str
    applicant_email: str
    applicant_phone: Optional[str]
    cover_letter: Optional[str]
    resume_filename: Optional[str]
    resume_url: Optional[str]
    ai_score: Optional[float]
    ai_comments: Optional[str]
    ai_analysis_status: str
    ai_analysis_error: Optional[str]
    status: str
    admin_notes: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ApplicationListResponse(BaseModel):
    """Paginated response for application list."""
    items: List[ApplicationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ApplicationStatusUpdate(BaseModel):
    """Schema for updating application status."""
    status: str = Field(..., description="New status: reviewed, shortlisted, contacted, rejected, hired")
    admin_notes: Optional[str] = None


class BulkRejectRequest(BaseModel):
    """Schema for bulk rejecting applications."""
    admin_notes: Optional[str] = Field(None, description="Note to add to all rejected applications")


class BulkRejectResponse(BaseModel):
    """Response for bulk reject operation."""
    success: bool
    rejected_count: int
    message: str


class JobStatsResponse(BaseModel):
    """Stats for a job's applications."""
    total_applications: int
    by_status: dict
    by_analysis_status: dict
    average_score: Optional[float]


class ApplicationSubmitResponse(BaseModel):
    """Response after submitting an application."""
    success: bool
    message: str
    application_id: Optional[int] = None
