from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.session import Base


class ReportType(Base):
    """
    Model for storing report types.
    Acts as a lookup table for different reports in the system.
    """
    __tablename__ = "report_types"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "customer_visit"
    name = Column(String(100), nullable=False)  # e.g., "Customer Visit Report"
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to recipients - cascade delete
    recipients = relationship(
        "ReportRecipient", 
        back_populates="report_type",
        cascade="all, delete-orphan"
    )
    
    # Relationship to files - cascade delete
    files = relationship(
        "ReportFile",
        back_populates="report_type",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<ReportType(id={self.id}, code='{self.code}', name='{self.name}')>"


class ReportRecipient(Base):
    """
    Model for storing email recipients for different reports.
    Each report type can have multiple recipients.
    """
    __tablename__ = "report_recipients"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    report_type_id = Column(Integer, ForeignKey("report_types.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_cc = Column(Boolean, default=False, nullable=False)  # CC recipient
    is_bcc = Column(Boolean, default=False, nullable=False)  # BCC recipient
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to report type
    report_type = relationship("ReportType", back_populates="recipients")
    
    def __repr__(self):
        return f"<ReportRecipient(id={self.id}, email='{self.email}', report_type_id={self.report_type_id})>"
