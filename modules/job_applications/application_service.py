from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc
from typing import List, Optional, Tuple
from datetime import datetime
from models.job import Job, JobApplication, JobStatus, ApplicationStatus, AIAnalysisStatus
from utils.logger import get_logger

logger = get_logger("app.modules.job_applications.application_service")


class JobApplicationService:
    """
    Service for managing job applications.
    Handles CRUD operations for JobApplication model.
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
    
    def get_application_by_id(self, application_id: int) -> Optional[JobApplication]:
        """Get an application by ID with job details."""
        return self.db.query(JobApplication).options(
            joinedload(JobApplication.job)
        ).filter(JobApplication.id == application_id).first()
    
    def get_applications_for_job(
        self,
        job_id: int,
        sort_by_score: bool = True,
        status: Optional[str] = None,
        ai_status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[JobApplication]:
        """
        Get all applications for a specific job.
        
        Args:
            job_id: Job ID to get applications for
            sort_by_score: If True, sort by AI score descending (highest first)
            status: Filter by application status
            ai_status: Filter by AI analysis status
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of JobApplication objects
        """
        query = self.db.query(JobApplication).filter(JobApplication.job_id == job_id)
        
        if status:
            query = query.filter(JobApplication.status == status)
        
        if ai_status:
            query = query.filter(JobApplication.ai_analysis_status == ai_status)
        
        # Sort by AI score (highest first) or by submission date
        if sort_by_score:
            # Put completed analyses first, sorted by score, then pending ones
            query = query.order_by(
                desc(JobApplication.ai_score.isnot(None)),  # Scored first
                desc(JobApplication.ai_score),              # Highest score first
                desc(JobApplication.created_at)             # Then by date
            )
        else:
            query = query.order_by(desc(JobApplication.created_at))
        
        if limit is not None:
            query = query.offset(offset).limit(limit)
        
        return query.all()
    
    def get_pending_analysis_applications(self, limit: int = 10) -> List[JobApplication]:
        """
        Get applications pending AI analysis.
        
        Args:
            limit: Maximum number of applications to retrieve
            
        Returns:
            List of JobApplication objects pending analysis
        """
        return self.db.query(JobApplication).options(
            joinedload(JobApplication.job)
        ).filter(
            JobApplication.ai_analysis_status == AIAnalysisStatus.PENDING.value
        ).order_by(
            asc(JobApplication.created_at)  # Process oldest first
        ).limit(limit).all()
    
    def count_applications_for_job(
        self, 
        job_id: int,
        status: Optional[str] = None,
        ai_status: Optional[str] = None
    ) -> int:
        """Get count of applications for a job with optional filters."""
        query = self.db.query(JobApplication).filter(JobApplication.job_id == job_id)
        
        if status:
            query = query.filter(JobApplication.status == status)
        
        if ai_status:
            query = query.filter(JobApplication.ai_analysis_status == ai_status)
        
        return query.count()
    
    def check_duplicate_application(self, job_id: int, email: str) -> bool:
        """Check if an application already exists for this job and email."""
        existing = self.db.query(JobApplication).filter(
            JobApplication.job_id == job_id,
            JobApplication.applicant_email == email
        ).first()
        return existing is not None
    
    # ==========================================================================
    # CRUD Operations
    # ==========================================================================
    
    def create_application(
        self,
        job_id: int,
        applicant_name: str,
        applicant_email: str,
        applicant_phone: Optional[str] = None,
        cover_letter: Optional[str] = None,
        resume_filename: Optional[str] = None,
        resume_path: Optional[str] = None,
        resume_url: Optional[str] = None
    ) -> Tuple[Optional[JobApplication], Optional[str]]:
        """
        Create a new job application.
        
        Args:
            job_id: ID of the job being applied to
            applicant_name: Name of applicant
            applicant_email: Email of applicant
            applicant_phone: Phone number (optional)
            cover_letter: Cover letter text (optional)
            resume_filename: Original filename of resume
            resume_path: File system path to resume
            resume_url: Public URL to resume
            
        Returns:
            Tuple of (JobApplication, error_message)
            Returns (None, error) if validation fails
        """
        # Check job exists and is published
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None, "Job not found"
        
        if job.status != JobStatus.PUBLISHED.value:
            return None, "Job is not accepting applications"
        
        # Check for duplicate application
        if self.check_duplicate_application(job_id, applicant_email):
            return None, "You have already applied for this position"
        
        application = JobApplication(
            job_id=job_id,
            applicant_name=applicant_name,
            applicant_email=applicant_email,
            applicant_phone=applicant_phone,
            cover_letter=cover_letter,
            resume_filename=resume_filename,
            resume_path=resume_path,
            resume_url=resume_url,
            status=ApplicationStatus.SUBMITTED.value,
            ai_analysis_status=AIAnalysisStatus.PENDING.value
        )
        
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        
        logger.info(f"Created application {application.id} for job {job_id} from {applicant_email}")
        return application, None
    
    def update_resume_text(self, application_id: int, resume_text: str) -> Optional[JobApplication]:
        """
        Update the extracted resume text for an application.
        
        Args:
            application_id: Application ID
            resume_text: Extracted text from resume PDF
            
        Returns:
            Updated application or None if not found
        """
        application = self.db.query(JobApplication).filter(
            JobApplication.id == application_id
        ).first()
        
        if not application:
            return None
        
        application.resume_text = resume_text
        self.db.commit()
        self.db.refresh(application)
        
        logger.info(f"Updated resume text for application {application_id}")
        return application
    
    def update_ai_analysis(
        self,
        application_id: int,
        score: float,
        comments: str,
        status: str = AIAnalysisStatus.COMPLETED.value
    ) -> Optional[JobApplication]:
        """
        Update AI analysis results for an application.
        
        Args:
            application_id: Application ID
            score: AI score (0-10)
            comments: AI-generated comments
            status: Analysis status
            
        Returns:
            Updated application or None if not found
        """
        application = self.db.query(JobApplication).filter(
            JobApplication.id == application_id
        ).first()
        
        if not application:
            return None
        
        # Ensure score is within bounds
        score = max(0.0, min(10.0, score))
        
        application.ai_score = score
        application.ai_comments = comments
        application.ai_analysis_status = status
        
        self.db.commit()
        self.db.refresh(application)
        
        logger.info(f"Updated AI analysis for application {application_id}: score={score}")
        return application
    
    def set_ai_analysis_status(
        self,
        application_id: int,
        status: str,
        error: Optional[str] = None
    ) -> Optional[JobApplication]:
        """
        Set AI analysis status (for tracking processing state).
        
        Args:
            application_id: Application ID
            status: New status
            error: Error message if failed
            
        Returns:
            Updated application or None if not found
        """
        application = self.db.query(JobApplication).filter(
            JobApplication.id == application_id
        ).first()
        
        if not application:
            return None
        
        application.ai_analysis_status = status
        if error:
            application.ai_analysis_error = error
        
        self.db.commit()
        self.db.refresh(application)
        
        return application
    
    def update_application_status(
        self,
        application_id: int,
        status: str,
        admin_notes: Optional[str] = None
    ) -> Optional[JobApplication]:
        """
        Update application status (admin action).
        
        Args:
            application_id: Application ID
            status: New status (reviewed, shortlisted, contacted, rejected, hired)
            admin_notes: Optional admin notes
            
        Returns:
            Updated application or None if not found
        """
        application = self.db.query(JobApplication).filter(
            JobApplication.id == application_id
        ).first()
        
        if not application:
            return None
        
        # Validate status
        valid_statuses = [s.value for s in ApplicationStatus]
        if status not in valid_statuses:
            logger.warning(f"Invalid status: {status}")
            return None
        
        application.status = status
        
        if admin_notes is not None:
            application.admin_notes = admin_notes
        
        # Track when reviewed
        if status in [ApplicationStatus.REVIEWED.value, ApplicationStatus.SHORTLISTED.value]:
            application.reviewed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(application)
        
        logger.info(f"Updated application {application_id} status to {status}")
        return application
    
    def delete_application(self, application_id: int) -> bool:
        """
        Delete an application.
        
        Args:
            application_id: Application ID
            
        Returns:
            True if deleted, False if not found
        """
        application = self.db.query(JobApplication).filter(
            JobApplication.id == application_id
        ).first()
        
        if not application:
            return False
        
        self.db.delete(application)
        self.db.commit()
        
        logger.info(f"Deleted application {application_id}")
        return True
    
    # ==========================================================================
    # Statistics
    # ==========================================================================
    
    def get_job_application_stats(self, job_id: int) -> dict:
        """
        Get statistics for applications on a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Dictionary with stats
        """
        total = self.count_applications_for_job(job_id)
        
        # Count by status
        status_counts = {}
        for status in ApplicationStatus:
            count = self.db.query(JobApplication).filter(
                JobApplication.job_id == job_id,
                JobApplication.status == status.value
            ).count()
            status_counts[status.value] = count
        
        # Count by analysis status
        analysis_counts = {}
        for status in AIAnalysisStatus:
            count = self.db.query(JobApplication).filter(
                JobApplication.job_id == job_id,
                JobApplication.ai_analysis_status == status.value
            ).count()
            analysis_counts[status.value] = count
        
        # Average score (for completed analyses)
        from sqlalchemy import func
        avg_score = self.db.query(func.avg(JobApplication.ai_score)).filter(
            JobApplication.job_id == job_id,
            JobApplication.ai_score.isnot(None)
        ).scalar()
        
        return {
            "total_applications": total,
            "by_status": status_counts,
            "by_analysis_status": analysis_counts,
            "average_score": round(avg_score, 2) if avg_score else None
        }

    def reject_remaining_applications(
        self,
        job_id: int,
        admin_notes: Optional[str] = None
    ) -> int:
        """
        Reject all applications that are still in submitted or reviewed status.
        Used when HR has shortlisted candidates and wants to reject the rest.
        
        Args:
            job_id: Job ID
            admin_notes: Optional note to add to rejected applications
            
        Returns:
            Number of applications rejected
        """
        # Statuses that should be rejected (not yet decided)
        pending_statuses = [
            ApplicationStatus.SUBMITTED.value,
            ApplicationStatus.REVIEWED.value
        ]
        
        applications = self.db.query(JobApplication).filter(
            JobApplication.job_id == job_id,
            JobApplication.status.in_(pending_statuses)
        ).all()
        
        count = 0
        for app in applications:
            app.status = ApplicationStatus.REJECTED.value
            if admin_notes:
                app.admin_notes = admin_notes
            count += 1
        
        if count > 0:
            self.db.commit()
            logger.info(f"Bulk rejected {count} applications for job {job_id}")
        
        return count
