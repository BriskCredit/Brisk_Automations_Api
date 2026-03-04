from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import List, Optional
from datetime import datetime, timezone
from models.job import Job, JobStatus
from utils.logger import get_logger

logger = get_logger("app.modules.job_applications.job_service")


class JobService:
    """
    Service for managing job postings.
    Handles CRUD operations for Job model.
    """
    
    def __init__(self, db: Session):
        """
        Initialize with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # ==========================================================================
    # Query Methods
    # ==========================================================================
    
    def get_job_by_id(self, job_id: int) -> Optional[Job]:
        """Get a job by ID."""
        return self.db.query(Job).filter(Job.id == job_id).first()
    
    def get_all_jobs(
        self,
        status: Optional[str] = None,
        include_expired: bool = True,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Job]:
        """
        Get all jobs with optional filtering and pagination.
        
        Args:
            status: Filter by job status (draft, published, closed)
            include_expired: Whether to include expired jobs (default True for admin)
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of Job objects
        """
        query = self.db.query(Job)
        
        if status:
            query = query.filter(Job.status == status)
        
        if not include_expired:
            now = datetime.now(timezone.utc)
            query = query.filter(
                or_(
                    Job.expires_at.is_(None),
                    Job.expires_at > now
                )
            )
        
        query = query.order_by(desc(Job.created_at))
        
        if limit is not None:
            query = query.offset(offset).limit(limit)
        
        return query.all()
    
    def get_published_jobs(
        self,
        include_expired: bool = False,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Job]:
        """Get all published jobs for public display (excludes expired by default)."""
        query = self.db.query(Job).filter(Job.status == JobStatus.PUBLISHED.value)
        
        if not include_expired:
            now = datetime.now(timezone.utc)
            query = query.filter(
                or_(
                    Job.expires_at.is_(None),
                    Job.expires_at > now
                )
            )
        
        query = query.order_by(desc(Job.published_at))
        
        if limit is not None:
            query = query.offset(offset).limit(limit)
        
        return query.all()
    
    def get_active_jobs(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Job]:
        """Get only active jobs (published and not expired)."""
        now = datetime.now(timezone.utc)
        query = self.db.query(Job).filter(
            Job.status == JobStatus.PUBLISHED.value,
            or_(
                Job.expires_at.is_(None),
                Job.expires_at > now
            )
        )
        query = query.order_by(desc(Job.published_at))
        
        if limit is not None:
            query = query.offset(offset).limit(limit)
        
        return query.all()
    
    def get_expired_jobs(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Job]:
        """Get expired jobs."""
        now = datetime.now(timezone.utc)
        query = self.db.query(Job).filter(
            Job.expires_at.isnot(None),
            Job.expires_at <= now
        )
        query = query.order_by(desc(Job.expires_at))
        
        if limit is not None:
            query = query.offset(offset).limit(limit)
        
        return query.all()
    
    def count_jobs(self, status: Optional[str] = None, include_expired: bool = True) -> int:
        """Get total count of jobs with optional status filter."""
        query = self.db.query(Job)
        if status:
            query = query.filter(Job.status == status)
        
        if not include_expired:
            now = datetime.now(timezone.utc)
            query = query.filter(
                or_(
                    Job.expires_at.is_(None),
                    Job.expires_at > now
                )
            )
        
        return query.count()
    
    def count_published_jobs(self, include_expired: bool = False) -> int:
        """Get count of published jobs."""
        query = self.db.query(Job).filter(Job.status == JobStatus.PUBLISHED.value)
        
        if not include_expired:
            now = datetime.now(timezone.utc)
            query = query.filter(
                or_(
                    Job.expires_at.is_(None),
                    Job.expires_at > now
                )
            )
        
        return query.count()
    
    def count_active_jobs(self) -> int:
        """Get count of active jobs (published and not expired)."""
        now = datetime.now(timezone.utc)
        return self.db.query(Job).filter(
            Job.status == JobStatus.PUBLISHED.value,
            or_(
                Job.expires_at.is_(None),
                Job.expires_at > now
            )
        ).count()
    
    def count_expired_jobs(self) -> int:
        """Get count of expired jobs."""
        now = datetime.now(timezone.utc)
        return self.db.query(Job).filter(
            Job.expires_at.isnot(None),
            Job.expires_at <= now
        ).count()
    
    # ==========================================================================
    # CRUD Operations
    # ==========================================================================
    
    def create_job(
        self,
        title: str,
        summary: Optional[str] = None,
        responsibilities: Optional[str] = None,
        requirements: Optional[str] = None,
        qualifications: Optional[str] = None,
        benefits: Optional[str] = None,
        notes: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        location: Optional[str] = None,
        department: Optional[str] = None,
        employment_type: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Job:
        """
        Create a new job posting in draft status.
        
        Args:
            title: Job title
            summary: Job summary/overview
            responsibilities: Job responsibilities
            requirements: Required qualifications
            qualifications: Preferred qualifications
            benefits: Job benefits
            notes: Internal admin notes
            custom_instructions: AI instructions for CV analysis
            location: Job location
            department: Department name
            employment_type: Type of employment
            expires_at: Expiry date for the job posting
            
        Returns:
            Created Job object
        """
        job = Job(
            title=title,
            summary=summary,
            responsibilities=responsibilities,
            requirements=requirements,
            qualifications=qualifications,
            benefits=benefits,
            notes=notes,
            custom_instructions=custom_instructions,
            status=JobStatus.DRAFT.value,
            location=location,
            department=department,
            employment_type=employment_type,
            expires_at=expires_at
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Created job: {job.id} - {job.title}")
        return job
    
    def update_job(self, job_id: int, **kwargs) -> Optional[Job]:
        """
        Update a job posting.
        
        Args:
            job_id: ID of job to update
            **kwargs: Fields to update
            
        Returns:
            Updated Job or None if not found
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return None
        
        allowed_fields = {
            'title', 'summary', 'responsibilities', 'requirements',
            'qualifications', 'benefits', 'notes', 'custom_instructions',
            'location', 'department', 'employment_type', 'expires_at'
        }
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(job, key, value)
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Updated job: {job.id}")
        return job
    
    def publish_job(self, job_id: int) -> Optional[Job]:
        """
        Publish a job (change status from draft to published).
        
        Args:
            job_id: ID of job to publish
            
        Returns:
            Published Job or None if not found or not in draft status
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return None
        
        if job.status != JobStatus.DRAFT.value:
            logger.warning(f"Cannot publish job {job_id}: status is {job.status}")
            return None
        
        job.status = JobStatus.PUBLISHED.value
        job.published_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Published job: {job.id} - {job.title}")
        return job
    
    def close_job(self, job_id: int) -> Optional[Job]:
        """
        Close a job posting (no more applications accepted).
        
        Args:
            job_id: ID of job to close
            
        Returns:
            Closed Job or None if not found
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return None
        
        job.status = JobStatus.CLOSED.value
        job.closed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Closed job: {job.id} - {job.title}")
        return job
    
    def reopen_job(self, job_id: int) -> Optional[Job]:
        """
        Reopen a closed job (set back to published).
        
        Args:
            job_id: ID of job to reopen
            
        Returns:
            Reopened Job or None if not found or not closed
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return None
        
        if job.status != JobStatus.CLOSED.value:
            logger.warning(f"Cannot reopen job {job_id}: status is {job.status}")
            return None
        
        job.status = JobStatus.PUBLISHED.value
        job.closed_at = None
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Reopened job: {job.id} - {job.title}")
        return job
    
    def delete_job(self, job_id: int) -> bool:
        """
        Delete a job posting (only allowed if in draft status).
        
        Args:
            job_id: ID of job to delete
            
        Returns:
            True if deleted, False if not found or not in draft status
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return False
        
        if job.status != JobStatus.DRAFT.value:
            logger.warning(f"Cannot delete job {job_id}: status is {job.status}")
            return False
        
        self.db.delete(job)
        self.db.commit()
        
        logger.info(f"Deleted job: {job_id}")
        return True
    
    def force_delete_job(self, job_id: int) -> bool:
        """
        Force delete a job regardless of status (admin only).
        
        Args:
            job_id: ID of job to delete
            
        Returns:
            True if deleted, False if not found
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return False
        
        self.db.delete(job)
        self.db.commit()
        
        logger.info(f"Force deleted job: {job_id}")
        return True
