from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime, date
from models.report_file import ReportFile
from models.report_recipient import ReportType
from utils.logger import get_logger

logger = get_logger("app.common.file_service")


class FileService:
    """
    Service for managing report file records in the database.
    Handles CRUD operations for ReportFile model.
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
    
    def get_file_by_id(self, file_id: int) -> Optional[ReportFile]:
        """Get a file by ID."""
        return self.db.query(ReportFile).filter(ReportFile.id == file_id).first()
    
    def get_file_by_path(self, file_path: str) -> Optional[ReportFile]:
        """Get a file by its storage path."""
        return self.db.query(ReportFile).filter(ReportFile.file_path == file_path).first()
    
    def get_files_by_report_type(
        self, 
        report_type_code: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[ReportFile]:
        """
        Get all files for a specific report type.
        
        Args:
            report_type_code: Report type code (e.g., 'customer_visit')
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of ReportFile objects ordered by creation date (newest first)
        """
        report_type = self.db.query(ReportType).filter(
            ReportType.code == report_type_code
        ).first()
        
        if not report_type:
            logger.warning(f"Report type '{report_type_code}' not found")
            return []
        
        return self.db.query(ReportFile).filter(
            ReportFile.report_type_id == report_type.id
        ).order_by(desc(ReportFile.created_at)).offset(offset).limit(limit).all()
    
    def get_files_by_date_range(
        self,
        start_date: date,
        end_date: date,
        report_type_code: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[ReportFile]:
        """
        Get files within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            report_type_code: Optional filter by report type
            limit: Maximum number of results (None for unlimited)
            offset: Number of results to skip
            
        Returns:
            List of ReportFile objects
        """
        query = self.db.query(ReportFile).filter(
            and_(
                ReportFile.created_at >= start_date,
                ReportFile.created_at <= end_date
            )
        )
        
        if report_type_code:
            report_type = self.db.query(ReportType).filter(
                ReportType.code == report_type_code
            ).first()
            if report_type:
                query = query.filter(ReportFile.report_type_id == report_type.id)
        
        query = query.order_by(desc(ReportFile.created_at))
        if limit is not None:
            query = query.offset(offset).limit(limit)
        return query.all()
    
    def count_files_by_date_range(
        self,
        start_date: date,
        end_date: date,
        report_type_code: Optional[str] = None
    ) -> int:
        """
        Count files within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            report_type_code: Optional filter by report type
            
        Returns:
            Count of files
        """
        query = self.db.query(ReportFile).filter(
            and_(
                ReportFile.created_at >= start_date,
                ReportFile.created_at <= end_date
            )
        )
        
        if report_type_code:
            report_type = self.db.query(ReportType).filter(
                ReportType.code == report_type_code
            ).first()
            if report_type:
                query = query.filter(ReportFile.report_type_id == report_type.id)
        
        return query.count()
    
    def search_files(
        self,
        filename_pattern: Optional[str] = None,
        report_type_code: Optional[str] = None,
        limit: int = 100
    ) -> List[ReportFile]:
        """
        Search files by filename pattern.
        
        Args:
            filename_pattern: Pattern to search in filename (SQL LIKE)
            report_type_code: Optional filter by report type
            limit: Maximum results
            
        Returns:
            List of matching ReportFile objects
        """
        query = self.db.query(ReportFile).options(joinedload(ReportFile.report_type))
        
        if filename_pattern:
            query = query.filter(ReportFile.filename.ilike(f"%{filename_pattern}%"))
        
        if report_type_code:
            report_type = self.db.query(ReportType).filter(
                ReportType.code == report_type_code
            ).first()
            if report_type:
                query = query.filter(ReportFile.report_type_id == report_type.id)
        
        return query.order_by(desc(ReportFile.created_at)).limit(limit).all()
    
    def get_recent_files(
        self, 
        limit: int = 20,
        offset: int = 0,
        report_type_code: Optional[str] = None
    ) -> List[ReportFile]:
        """Get the most recent files across all report types (or filtered by type)."""
        query = self.db.query(ReportFile).options(
            joinedload(ReportFile.report_type)
        )
        
        if report_type_code:
            report_type = self.db.query(ReportType).filter(
                ReportType.code == report_type_code
            ).first()
            if report_type:
                query = query.filter(ReportFile.report_type_id == report_type.id)
        
        return query.order_by(desc(ReportFile.created_at)).offset(offset).limit(limit).all()
    
    def count_files_by_report_type(self, report_type_code: str) -> int:
        """Get total count of files for a specific report type."""
        report_type = self.db.query(ReportType).filter(
            ReportType.code == report_type_code
        ).first()
        
        if not report_type:
            return 0
        
        return self.db.query(ReportFile).filter(
            ReportFile.report_type_id == report_type.id
        ).count()
    
    # ==========================================================================
    # CRUD Operations
    # ==========================================================================
    
    def create_file_record(
        self,
        filename: str,
        file_path: str,
        file_url: str,
        report_type_id: int,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        report_date: Optional[datetime] = None
    ) -> Optional[ReportFile]:
        """
        Create a new file record in the database.
        
        Args:
            filename: Original filename
            file_path: Relative storage path
            file_url: Full download URL
            report_type_id: Report type ID (foreign key)
            file_size: File size in bytes
            mime_type: MIME type
            report_date: Date the report covers
            
        Returns:
            Created ReportFile or None on error
        """
        # Check for duplicate
        existing = self.get_file_by_path(file_path)
        if existing:
            logger.warning(f"File record already exists for path: {file_path}")
            return existing
        
        file_record = ReportFile(
            filename=filename,
            file_path=file_path,
            file_url=file_url,
            file_size=file_size,
            mime_type=mime_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            report_type_id=report_type_id,
            report_date=report_date
        )
        
        self.db.add(file_record)
        self.db.commit()
        self.db.refresh(file_record)
        
        logger.info(f"Created file record: {filename} (ID: {file_record.id})")
        return file_record
    
    def delete_file_record(self, file_id: int) -> bool:
        """
        Delete a file record from the database.
        
        Note: This only deletes the DB record, not the actual file.
        Use FileStorageService to delete the physical file.
        
        Args:
            file_id: ID of the file record to delete
            
        Returns:
            True if deleted, False if not found
        """
        file_record = self.get_file_by_id(file_id)
        if not file_record:
            return False
        
        self.db.delete(file_record)
        self.db.commit()
        
        logger.info(f"Deleted file record ID: {file_id}")
        return True
    
    # ==========================================================================
    # Statistics
    # ==========================================================================
    
    def get_file_count(self, report_type_code: Optional[str] = None) -> int:
        """Get total count of files, optionally filtered by report type."""
        query = self.db.query(ReportFile)
        
        if report_type_code:
            report_type = self.db.query(ReportType).filter(
                ReportType.code == report_type_code
            ).first()
            if report_type:
                query = query.filter(ReportFile.report_type_id == report_type.id)
        
        return query.count()
    
    def get_total_storage_size(self, report_type_code: Optional[str] = None) -> int:
        """Get total storage size in bytes, optionally filtered by report type."""
        from sqlalchemy import func
        
        query = self.db.query(func.sum(ReportFile.file_size))
        
        if report_type_code:
            report_type = self.db.query(ReportType).filter(
                ReportType.code == report_type_code
            ).first()
            if report_type:
                query = query.filter(ReportFile.report_type_id == report_type.id)
        
        result = query.scalar()
        return result or 0
