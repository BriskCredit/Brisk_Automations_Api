import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status, BackgroundTasks
from pydantic import EmailStr
from typing import Optional
from sqlalchemy.orm import Session
from database.session import get_db
from modules.job_applications.job_service import JobService
from modules.job_applications.application_service import JobApplicationService
from modules.job_applications.resume_parser import ResumeParserService
from modules.job_applications.ai_analysis import AIAnalysisService
from models.job import JobStatus, AIAnalysisStatus
from common.pagination import create_paginated_response
from common.file_storage_service import FileStorageService
from utils.logger import get_logger
from schemas.jobs import (
    PublicJobResponse,
    PublicJobListResponse,
    ApplicationSubmitResponse,
)
from schemas.common import MessageResponse

logger = get_logger("app.controllers.jobs")

router = APIRouter(prefix="/jobs", tags=["Jobs - Public"])


# =============================================================================
# Background Tasks
# =============================================================================

def process_application_background(
    application_id: int,
    resume_path: str,
    job_id: int
):
    """
    Background task to process an application:
    1. Extract text from resume PDF
    2. Run AI analysis
    3. Update application with results
    """
    from database.session import SessionLocal
    from common.file_storage_service import FileStorageService
    
    db = SessionLocal()
    try:
        app_service = JobApplicationService(db)
        job_service = JobService(db)
        resume_parser = ResumeParserService()
        ai_service = AIAnalysisService()
        file_storage = FileStorageService()
        
        # Mark as processing
        app_service.set_ai_analysis_status(application_id, AIAnalysisStatus.PROCESSING.value)
        
        # Get job details
        job = job_service.get_job_by_id(job_id)
        if not job:
            app_service.set_ai_analysis_status(
                application_id, 
                AIAnalysisStatus.FAILED.value,
                error="Job not found"
            )
            return
        
        # Get absolute path to resume file
        absolute_resume_path = str(file_storage.get_file_path(resume_path))
        
        # Extract text from resume
        logger.info(f"Extracting text from resume for application {application_id}")
        resume_text, extract_error = resume_parser.extract_text_from_pdf(absolute_resume_path)
        
        if extract_error:
            logger.error(f"Resume extraction failed for application {application_id}: {extract_error}")
            app_service.set_ai_analysis_status(
                application_id,
                AIAnalysisStatus.FAILED.value,
                error=f"Resume extraction failed: {extract_error}"
            )
            return
        
        # Update resume text
        app_service.update_resume_text(application_id, resume_text)
        
        # Run AI analysis
        logger.info(f"Running AI analysis for application {application_id}")
        result, ai_error = ai_service.analyze_cv(
            resume_text=resume_text,
            job_title=job.title,
            job_summary=job.summary,
            job_requirements=job.requirements,
            job_responsibilities=job.responsibilities,
            job_qualifications=job.qualifications,
            custom_instructions=job.custom_instructions
        )
        
        if ai_error:
            logger.error(f"AI analysis failed for application {application_id}: {ai_error}")
            app_service.set_ai_analysis_status(
                application_id,
                AIAnalysisStatus.FAILED.value,
                error=f"AI analysis failed: {ai_error}"
            )
            return
        
        # Format comments for storage
        comments = ai_service.format_analysis_for_display(result)
        
        # Update application with AI results
        app_service.update_ai_analysis(
            application_id=application_id,
            score=result.score,
            comments=comments,
            status=AIAnalysisStatus.COMPLETED.value
        )
        
        logger.info(f"AI analysis completed for application {application_id}: score={result.score}")
        
    except Exception as e:
        logger.error(f"Background processing failed for application {application_id}: {e}")
        try:
            app_service.set_ai_analysis_status(
                application_id,
                AIAnalysisStatus.FAILED.value,
                error=str(e)
            )
        except:
            pass
    finally:
        db.close()


# =============================================================================
# Public Job Endpoints
# =============================================================================

@router.get("", response_model=PublicJobListResponse)
def list_published_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    db: Session = Depends(get_db)
):
    """List all published jobs available for application."""
    service = JobService(db)
    
    offset = (page - 1) * page_size
    jobs = service.get_published_jobs(limit=page_size, offset=offset)
    total = service.count_published_jobs()
    
    # Convert to public response (exclude admin fields)
    items = []
    for job in jobs:
        items.append(PublicJobResponse(
            id=job.id,
            title=job.title,
            summary=job.summary,
            responsibilities=job.responsibilities,
            requirements=job.requirements,
            qualifications=job.qualifications,
            benefits=job.benefits,
            location=job.location,
            department=job.department,
            employment_type=job.employment_type,
            published_at=job.published_at
        ))
    
    return create_paginated_response(items=items, total=total, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=PublicJobResponse)
def get_published_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific published job by ID."""
    service = JobService(db)
    
    job = service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != JobStatus.PUBLISHED.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return PublicJobResponse(
        id=job.id,
        title=job.title,
        summary=job.summary,
        responsibilities=job.responsibilities,
        requirements=job.requirements,
        qualifications=job.qualifications,
        benefits=job.benefits,
        location=job.location,
        department=job.department,
        employment_type=job.employment_type,
        published_at=job.published_at
    )


@router.post("/{job_id}/apply", response_model=ApplicationSubmitResponse)
async def submit_application(
    job_id: int,
    background_tasks: BackgroundTasks,
    applicant_name: str = Form(..., min_length=1, max_length=255),
    applicant_email: EmailStr = Form(...),
    applicant_phone: Optional[str] = Form(None),
    cover_letter: Optional[str] = Form(None),
    resume: UploadFile = File(..., description="Resume/CV in PDF format"),
    db: Session = Depends(get_db)
):
    """
    Submit a job application with resume.
    
    The resume will be processed in the background:
    1. Text extraction from PDF
    2. AI analysis against job description
    3. Score and comments generation
    """
    job_service = JobService(db)
    app_service = JobApplicationService(db)
    
    # Verify job exists and is published
    job = job_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != JobStatus.PUBLISHED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This job is not accepting applications"
        )
    
    # Validate resume file
    if not resume.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume must be a PDF file"
        )
    
    if resume.size and resume.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume file size must be less than 10MB"
        )
    
    # Save resume file
    try:
        file_storage = FileStorageService()
        
        # Generate unique filename
        file_ext = ".pdf"
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Create temp file
        temp_path = f"./uploads/temp/{unique_filename}"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        with open(temp_path, "wb") as buffer:
            content = await resume.read()
            buffer.write(content)
        
        # Move to permanent storage
        file_info = file_storage.save_file(
            source_path=temp_path,
            category="resumes",
            subcategory=str(job_id),
            filename=unique_filename,
            delete_source=True
        )
        
        resume_path = file_info["file_path"]
        resume_url = file_info["file_url"]
        
    except Exception as e:
        logger.error(f"Failed to save resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save resume file"
        )
    
    # Create application
    application, error = app_service.create_application(
        job_id=job_id,
        applicant_name=applicant_name,
        applicant_email=applicant_email,
        applicant_phone=applicant_phone,
        cover_letter=cover_letter,
        resume_filename=resume.filename,
        resume_path=resume_path,
        resume_url=resume_url
    )
    
    if error:
        # Clean up uploaded file
        try:
            os.remove(resume_path)
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Queue background processing for AI analysis
    background_tasks.add_task(
        process_application_background,
        application_id=application.id,
        resume_path=resume_path,
        job_id=job_id
    )
    
    return ApplicationSubmitResponse(
        success=True,
        message="Your application has been submitted successfully. We will review it shortly.",
        application_id=application.id
    )


@router.get("/{job_id}/check-application")
def check_application_status(
    job_id: int,
    email: EmailStr = Query(..., description="Email used in application"),
    db: Session = Depends(get_db)
):
    """
    Check if an application exists for a specific job and email.
    Returns basic status without sensitive details.
    """
    job_service = JobService(db)
    app_service = JobApplicationService(db)
    
    # Verify job exists
    job = job_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    has_applied = app_service.check_duplicate_application(job_id, email)
    
    return {
        "applied": has_applied,
        "message": "You have already applied for this position" if has_applied else "No application found"
    }
