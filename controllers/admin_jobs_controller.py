from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database.session import get_db
from modules.job_applications.job_service import JobService
from modules.job_applications.application_service import JobApplicationService
from models.job import JobStatus, ApplicationStatus, AIAnalysisStatus
from common.pagination import create_paginated_response


router = APIRouter(prefix="/admin/jobs", tags=["Admin - Jobs"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

# Job Schemas
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


# Application Schemas
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


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    success: bool = True


# =============================================================================
# Job CRUD Endpoints
# =============================================================================

@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    data: JobCreate,
    db: Session = Depends(get_db)
):
    """Create a new job posting. Set publish=true to publish immediately."""
    service = JobService(db)
    
    job = service.create_job(
        title=data.title,
        summary=data.summary,
        responsibilities=data.responsibilities,
        requirements=data.requirements,
        qualifications=data.qualifications,
        benefits=data.benefits,
        notes=data.notes,
        custom_instructions=data.custom_instructions,
        location=data.location,
        department=data.department,
        employment_type=data.employment_type,
        expires_at=data.expires_at
    )
    
    # Publish immediately if requested
    if data.publish:
        job = service.publish_job(job.id)
    
    return JobResponse(
        id=job.id,
        title=job.title,
        summary=job.summary,
        responsibilities=job.responsibilities,
        requirements=job.requirements,
        qualifications=job.qualifications,
        benefits=job.benefits,
        notes=job.notes,
        custom_instructions=job.custom_instructions,
        status=job.status,
        location=job.location,
        department=job.department,
        employment_type=job.employment_type,
        created_at=job.created_at,
        updated_at=job.updated_at,
        published_at=job.published_at,
        closed_at=job.closed_at,
        expires_at=job.expires_at,
        is_expired=job.is_expired,
        application_count=0
    )


@router.get("", response_model=JobListResponse)
def list_jobs(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: draft, published, closed"),
    include_expired: bool = Query(True, description="Include expired jobs"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(5, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """List all jobs with pagination."""
    job_service = JobService(db)
    app_service = JobApplicationService(db)
    
    offset = (page - 1) * page_size
    jobs = job_service.get_all_jobs(status=status_filter, include_expired=include_expired, limit=page_size, offset=offset)
    total = job_service.count_jobs(status=status_filter, include_expired=include_expired)
    
    # Add application count and expiry info to each job
    items = []
    for job in jobs:
        job_dict = {
            "id": job.id,
            "title": job.title,
            "summary": job.summary,
            "responsibilities": job.responsibilities,
            "requirements": job.requirements,
            "qualifications": job.qualifications,
            "benefits": job.benefits,
            "notes": job.notes,
            "custom_instructions": job.custom_instructions,
            "status": job.status,
            "location": job.location,
            "department": job.department,
            "employment_type": job.employment_type,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "published_at": job.published_at,
            "closed_at": job.closed_at,
            "expires_at": job.expires_at,
            "is_expired": job.is_expired,
            "application_count": app_service.count_applications_for_job(job.id)
        }
        items.append(JobResponse(**job_dict))
    
    return create_paginated_response(items=items, total=total, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific job by ID."""
    job_service = JobService(db)
    app_service = JobApplicationService(db)
    
    job = job_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    return JobResponse(
        id=job.id,
        title=job.title,
        summary=job.summary,
        responsibilities=job.responsibilities,
        requirements=job.requirements,
        qualifications=job.qualifications,
        benefits=job.benefits,
        notes=job.notes,
        custom_instructions=job.custom_instructions,
        status=job.status,
        location=job.location,
        department=job.department,
        employment_type=job.employment_type,
        created_at=job.created_at,
        updated_at=job.updated_at,
        published_at=job.published_at,
        closed_at=job.closed_at,
        expires_at=job.expires_at,
        is_expired=job.is_expired,
        application_count=app_service.count_applications_for_job(job.id)
    )


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    data: JobUpdate,
    db: Session = Depends(get_db)
):
    """Update a job posting."""
    service = JobService(db)
    
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    job = service.update_job(job_id, **update_data)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    return job


@router.post("/{job_id}/publish", response_model=JobResponse)
def publish_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Publish a draft job (make it visible on the website)."""
    service = JobService(db)
    
    job = service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    if job.status != JobStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is already {job.status}. Only draft jobs can be published."
        )
    
    published_job = service.publish_job(job_id)
    return published_job


@router.post("/{job_id}/close", response_model=JobResponse)
def close_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Close a job (stop accepting applications)."""
    service = JobService(db)
    
    job = service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    closed_job = service.close_job(job_id)
    return closed_job


@router.post("/{job_id}/reopen", response_model=JobResponse)
def reopen_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Reopen a closed job."""
    service = JobService(db)
    
    job = service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    if job.status != JobStatus.CLOSED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is {job.status}. Only closed jobs can be reopened."
        )
    
    reopened_job = service.reopen_job(job_id)
    return reopened_job


@router.delete("/{job_id}", response_model=MessageResponse)
def delete_job(
    job_id: int,
    force: bool = Query(False, description="Force delete regardless of status"),
    db: Session = Depends(get_db)
):
    """Delete a job. By default, only draft jobs can be deleted."""
    service = JobService(db)
    
    job = service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    if force:
        success = service.force_delete_job(job_id)
    else:
        if job.status != JobStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete {job.status} job. Use force=true to force delete."
            )
        success = service.delete_job(job_id)
    
    if success:
        return MessageResponse(message=f"Job {job_id} deleted successfully")
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to delete job"
    )


# =============================================================================
# Application Management Endpoints
# =============================================================================

@router.get("/{job_id}/applications", response_model=ApplicationListResponse)
def list_job_applications(
    job_id: int,
    sort_by_score: bool = Query(True, description="Sort by AI score (highest first)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by application status"),
    ai_status: Optional[str] = Query(None, description="Filter by AI analysis status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(5, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """List applications for a job, sorted by AI score by default."""
    job_service = JobService(db)
    app_service = JobApplicationService(db)
    
    # Verify job exists
    job = job_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    offset = (page - 1) * page_size
    applications = app_service.get_applications_for_job(
        job_id=job_id,
        sort_by_score=sort_by_score,
        status=status_filter,
        ai_status=ai_status,
        limit=page_size,
        offset=offset
    )
    total = app_service.count_applications_for_job(
        job_id=job_id,
        status=status_filter,
        ai_status=ai_status
    )
    
    return create_paginated_response(items=applications, total=total, page=page, page_size=page_size)


@router.get("/{job_id}/applications/stats", response_model=JobStatsResponse)
def get_job_application_stats(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get statistics for applications on a job."""
    job_service = JobService(db)
    app_service = JobApplicationService(db)
    
    # Verify job exists
    job = job_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    stats = app_service.get_job_application_stats(job_id)
    return stats


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific application by ID."""
    app_service = JobApplicationService(db)
    
    application = app_service.get_application_by_id(application_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found"
        )
    
    return application


@router.patch("/applications/{application_id}/status", response_model=ApplicationResponse)
def update_application_status(
    application_id: int,
    data: ApplicationStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update an application's status."""
    app_service = JobApplicationService(db)
    
    # Validate status
    valid_statuses = [s.value for s in ApplicationStatus]
    if data.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    application = app_service.update_application_status(
        application_id=application_id,
        status=data.status,
        admin_notes=data.admin_notes
    )
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found"
        )
    
    return application


@router.delete("/applications/{application_id}", response_model=MessageResponse)
def delete_application(
    application_id: int,
    db: Session = Depends(get_db)
):
    """Delete an application."""
    app_service = JobApplicationService(db)
    
    success = app_service.delete_application(application_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found"
        )
    
    return MessageResponse(message=f"Application {application_id} deleted successfully")


@router.post("/{job_id}/applications/reject-remaining", response_model=BulkRejectResponse)
def reject_remaining_applications(
    job_id: int,
    data: BulkRejectRequest = None,
    db: Session = Depends(get_db)
):
    """
    Reject all remaining applications that are still in 'submitted' or 'reviewed' status.
    Use this after shortlisting candidates to reject all others at once.
    """
    job_service = JobService(db)
    app_service = JobApplicationService(db)
    
    # Verify job exists
    job = job_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    admin_notes = data.admin_notes if data else None
    rejected_count = app_service.reject_remaining_applications(job_id, admin_notes)
    
    return BulkRejectResponse(
        success=True,
        rejected_count=rejected_count,
        message=f"Rejected {rejected_count} application(s)"
    )
