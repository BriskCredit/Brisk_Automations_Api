from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.session import Base


class ReportFile(Base):
    """
    Model for storing report file metadata.
    Tracks uploaded report files for download and management.
    """
    __tablename__ = "report_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)  # Original filename
    file_path = Column(String(500), nullable=False, unique=True)  # Relative path in storage
    file_url = Column(String(500), nullable=False)  # Full URL for download
    file_size = Column(BigInteger, nullable=True)  # Size in bytes
    mime_type = Column(String(100), nullable=True, default="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    report_type_id = Column(Integer, ForeignKey("report_types.id", ondelete="CASCADE"), nullable=False, index=True)
    report_date = Column(DateTime(timezone=True), nullable=True)  # Date the report covers
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to report type
    report_type = relationship("ReportType", back_populates="files")
    
    def __repr__(self):
        return f"<ReportFile(id={self.id}, filename='{self.filename}', report_type_id={self.report_type_id})>"
