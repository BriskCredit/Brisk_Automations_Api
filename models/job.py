from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.session import Base
import enum


class JobStatus(str, enum.Enum):
    """Status of a job posting."""
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class ApplicationStatus(str, enum.Enum):
    """Status of a job application."""
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    SHORTLISTED = "shortlisted"
    CONTACTED = "contacted"
    REJECTED = "rejected"
    HIRED = "hired"


class AIAnalysisStatus(str, enum.Enum):
    """Status of AI analysis for an application."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    """
    Job posting model containing the job description components.
    
    A standard JD typically includes:
    - Title: Job title/position name
    - Summary: Brief overview of the role and company context
    - Responsibilities: Day-to-day duties and expectations
    - Requirements: Must-have qualifications, skills, experience
    - Qualifications: Preferred/nice-to-have qualifications
    - Benefits: What the company offers (salary range, perks, etc.)
    - Notes: Internal notes (not shown to applicants)
    - Custom Instructions: AI-specific instructions for CV analysis (prioritized)
    """
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Core JD Fields
    title = Column(String(255), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    qualifications = Column(Text, nullable=True)  # Preferred/nice-to-have
    benefits = Column(Text, nullable=True)
    
    # Admin-only fields
    notes = Column(Text, nullable=True)  # Internal notes, not shown to applicants
    custom_instructions = Column(Text, nullable=True)  # AI instructions for CV analysis (priority)
    
    # Status and metadata
    status = Column(String(20), default=JobStatus.DRAFT.value, nullable=False, index=True)
    location = Column(String(255), nullable=True)
    department = Column(String(100), nullable=True)
    employment_type = Column(String(50), nullable=True)  # full-time, part-time, contract, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Job posting expiry date
    
    # Relationships
    applications = relationship("JobApplication", back_populates="job", cascade="all, delete-orphan")
    
    @property
    def is_expired(self) -> bool:
        """Check if the job posting has expired."""
        if self.expires_at is None:
            return False
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        # Handle timezone-naive expires_at by assuming it's UTC
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now > expires
    
    @property
    def is_active(self) -> bool:
        """Check if job is published and not expired."""
        return self.status == JobStatus.PUBLISHED.value and not self.is_expired
    
    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}', status='{self.status}')>"


class JobApplication(Base):
    """
    Job application submitted by a candidate.
    
    Contains applicant information, resume details, and AI analysis results.
    """
    __tablename__ = "job_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Applicant Information
    applicant_name = Column(String(255), nullable=False)
    applicant_email = Column(String(255), nullable=False, index=True)
    applicant_phone = Column(String(50), nullable=True)
    cover_letter = Column(Text, nullable=True)
    
    # Resume/CV
    resume_filename = Column(String(255), nullable=True)
    resume_path = Column(String(500), nullable=True)  # File system path
    resume_url = Column(String(500), nullable=True)   # Public URL
    resume_text = Column(Text, nullable=True)         # Extracted text from PDF
    
    # AI Analysis Results
    ai_score = Column(Float, nullable=True)           # Score out of 10
    ai_comments = Column(Text, nullable=True)         # AI-generated analysis comments
    ai_analysis_status = Column(
        String(20), 
        default=AIAnalysisStatus.PENDING.value, 
        nullable=False,
        index=True
    )
    ai_analysis_error = Column(Text, nullable=True)   # Error message if analysis failed
    
    # Application Status
    status = Column(String(20), default=ApplicationStatus.SUBMITTED.value, nullable=False, index=True)
    admin_notes = Column(Text, nullable=True)  # Notes added by admin during review
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    job = relationship("Job", back_populates="applications")
    
    def __repr__(self):
        return f"<JobApplication(id={self.id}, job_id={self.job_id}, applicant='{self.applicant_name}', score={self.ai_score})>"
