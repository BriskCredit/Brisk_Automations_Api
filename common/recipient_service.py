from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import List, Optional
from models.report_recipient import ReportRecipient, ReportType
from utils.logger import get_logger

logger = get_logger("app.common.recipient_service")


class RecipientService:
    """
    Service for managing report types and email recipients.
    Provides CRUD operations for ReportType and ReportRecipient models.
    """
    
    def __init__(self, db: Session):
        """
        Initialize with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # ==========================================================================
    # Report Type Methods
    # ==========================================================================
    
    def get_report_type_by_code(self, code: str) -> Optional[ReportType]:
        """Get a report type by its unique code."""
        return self.db.query(ReportType).filter(ReportType.code == code).first()
    
    def get_report_type_by_id(self, report_type_id: int) -> Optional[ReportType]:
        """Get a report type by ID."""
        return self.db.query(ReportType).filter(ReportType.id == report_type_id).first()
    
    def get_all_report_types(
        self, 
        active_only: bool = True,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[ReportType]:
        """Get all report types with optional pagination."""
        query = self.db.query(ReportType)
        if active_only:
            query = query.filter(ReportType.is_active == True)
        query = query.order_by(ReportType.id)
        if limit is not None:
            query = query.offset(offset).limit(limit)
        return query.all()
    
    def count_report_types(self, active_only: bool = True) -> int:
        """Get total count of report types."""
        query = self.db.query(ReportType)
        if active_only:
            query = query.filter(ReportType.is_active == True)
        return query.count()
    
    def create_report_type(
        self,
        code: str,
        name: str,
        description: Optional[str] = None
    ) -> ReportType:
        """
        Create a new report type.
        
        Args:
            code: Unique code identifier (e.g., 'customer_visit')
            name: Display name (e.g., 'Customer Visit Report')
            description: Optional description
            
        Returns:
            Created ReportType object
        """
        existing = self.get_report_type_by_code(code)
        if existing:
            logger.warning(f"Report type '{code}' already exists")
            return existing
        
        report_type = ReportType(
            code=code,
            name=name,
            description=description,
            is_active=True
        )
        
        self.db.add(report_type)
        self.db.commit()
        self.db.refresh(report_type)
        
        logger.info(f"Created report type: {code}")
        return report_type
    
    def update_report_type(
        self,
        report_type_id: int,
        **kwargs
    ) -> Optional[ReportType]:
        """
        Update a report type.
        
        Args:
            report_type_id: ID of report type to update
            **kwargs: Fields to update (name, description, is_active)
            
        Returns:
            Updated ReportType or None if not found
        """
        report_type = self.get_report_type_by_id(report_type_id)
        if not report_type:
            return None
        
        allowed_fields = {'name', 'description', 'is_active'}
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(report_type, key, value)
        
        self.db.commit()
        self.db.refresh(report_type)
        
        logger.info(f"Updated report type {report_type_id}")
        return report_type
    
    def delete_report_type(self, report_type_id: int) -> bool:
        """
        Delete a report type and all its recipients (cascade).
        
        Args:
            report_type_id: ID of report type to delete
            
        Returns:
            True if successful, False if not found
        """
        report_type = self.get_report_type_by_id(report_type_id)
        if not report_type:
            return False
        
        self.db.delete(report_type)
        self.db.commit()
        
        logger.info(f"Deleted report type {report_type_id} and all its recipients")
        return True
    
    # ==========================================================================
    # Recipient Query Methods
    # ==========================================================================
    
    def get_recipients_for_report(
        self, 
        report_type_code: str,
        active_only: bool = True
    ) -> dict:
        """
        Get all recipients for a specific report type by code.
        
        Args:
            report_type_code: The report type code (e.g., 'customer_visit')
            active_only: Only return active recipients
            
        Returns:
            Dict with 'to', 'cc', 'bcc' lists of email addresses
        """
        report_type = self.get_report_type_by_code(report_type_code)
        if not report_type:
            logger.warning(f"Report type '{report_type_code}' not found")
            return {"to": [], "cc": [], "bcc": []}
        
        query = self.db.query(ReportRecipient).filter(
            ReportRecipient.report_type_id == report_type.id
        )
        
        if active_only:
            query = query.filter(ReportRecipient.is_active == True)
        
        recipients = query.all()
        
        result = {
            "to": [],
            "cc": [],
            "bcc": []
        }
        
        for r in recipients:
            if r.is_bcc:
                result["bcc"].append(r.email)
            elif r.is_cc:
                result["cc"].append(r.email)
            else:
                result["to"].append(r.email)
        
        logger.debug(f"Found {len(recipients)} recipients for report '{report_type_code}'")
        return result
    
    def get_all_recipients(
        self, 
        report_type_code: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[ReportRecipient]:
        """
        Get all recipients, optionally filtered by report type code.
        
        Args:
            report_type_code: Optional filter by report type code
            limit: Maximum number of results (None for unlimited)
            offset: Number of results to skip
            
        Returns:
            List of ReportRecipient objects
        """
        query = self.db.query(ReportRecipient).options(joinedload(ReportRecipient.report_type))
        
        if report_type_code:
            report_type = self.get_report_type_by_code(report_type_code)
            if report_type:
                query = query.filter(ReportRecipient.report_type_id == report_type.id)
            else:
                return []
        
        query = query.order_by(ReportRecipient.id)
        if limit is not None:
            query = query.offset(offset).limit(limit)
        return query.all()
    
    def count_recipients(self, report_type_code: Optional[str] = None) -> int:
        """
        Get total count of recipients, optionally filtered by report type code.
        
        Args:
            report_type_code: Optional filter by report type code
            
        Returns:
            Count of recipients
        """
        query = self.db.query(ReportRecipient)
        
        if report_type_code:
            report_type = self.get_report_type_by_code(report_type_code)
            if report_type:
                query = query.filter(ReportRecipient.report_type_id == report_type.id)
            else:
                return 0
        
        return query.count()
    
    def get_recipient_by_id(self, recipient_id: int) -> Optional[ReportRecipient]:
        """Get a recipient by ID."""
        return self.db.query(ReportRecipient).filter(
            ReportRecipient.id == recipient_id
        ).first()
    
    def get_recipient_by_email_and_report(
        self, 
        email: str, 
        report_type_code: str
    ) -> Optional[ReportRecipient]:
        """Get a recipient by email and report type code combination."""
        report_type = self.get_report_type_by_code(report_type_code)
        if not report_type:
            return None
        
        return self.db.query(ReportRecipient).filter(
            and_(
                ReportRecipient.email == email,
                ReportRecipient.report_type_id == report_type.id
            )
        ).first()
    
    # ==========================================================================
    # Recipient CRUD Operations
    # ==========================================================================
    
    def add_recipient(
        self,
        email: str,
        report_type_code: str,
        name: Optional[str] = None,
        is_cc: bool = False,
        is_bcc: bool = False
    ) -> Optional[ReportRecipient]:
        """
        Add a new recipient for a report.
        
        Args:
            email: Email address
            report_type_code: Report type code identifier
            name: Optional recipient name
            is_cc: Whether this is a CC recipient
            is_bcc: Whether this is a BCC recipient
            
        Returns:
            Created ReportRecipient object, or None if report type doesn't exist
        """
        report_type = self.get_report_type_by_code(report_type_code)
        if not report_type:
            logger.error(f"Report type '{report_type_code}' not found. Create it first.")
            return None
        
        # Check if already exists
        existing = self.get_recipient_by_email_and_report(email, report_type_code)
        if existing:
            logger.warning(f"Recipient {email} already exists for {report_type_code}")
            return existing
        
        recipient = ReportRecipient(
            email=email,
            report_type_id=report_type.id,
            name=name,
            is_cc=is_cc,
            is_bcc=is_bcc,
            is_active=True
        )
        
        self.db.add(recipient)
        self.db.commit()
        self.db.refresh(recipient)
        
        logger.info(f"Added recipient {email} for report '{report_type_code}'")
        return recipient
    
    def update_recipient(
        self,
        recipient_id: int,
        **kwargs
    ) -> Optional[ReportRecipient]:
        """
        Update a recipient's details.
        
        Args:
            recipient_id: ID of recipient to update
            **kwargs: Fields to update (email, name, is_cc, is_bcc, is_active)
            
        Returns:
            Updated ReportRecipient or None if not found
        """
        recipient = self.get_recipient_by_id(recipient_id)
        if not recipient:
            return None
        
        allowed_fields = {'email', 'name', 'is_cc', 'is_bcc', 'is_active'}
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(recipient, key, value)
        
        self.db.commit()
        self.db.refresh(recipient)
        
        logger.info(f"Updated recipient {recipient_id}")
        return recipient
    
    def deactivate_recipient(self, recipient_id: int) -> bool:
        """
        Deactivate a recipient (soft delete).
        
        Args:
            recipient_id: ID of recipient to deactivate
            
        Returns:
            True if successful, False if not found
        """
        recipient = self.get_recipient_by_id(recipient_id)
        if not recipient:
            return False
        
        recipient.is_active = False
        self.db.commit()
        
        logger.info(f"Deactivated recipient {recipient_id}")
        return True
    
    def delete_recipient(self, recipient_id: int) -> bool:
        """
        Permanently delete a recipient.
        
        Args:
            recipient_id: ID of recipient to delete
            
        Returns:
            True if successful, False if not found
        """
        recipient = self.get_recipient_by_id(recipient_id)
        if not recipient:
            return False
        
        self.db.delete(recipient)
        self.db.commit()
        
        logger.info(f"Deleted recipient {recipient_id}")
        return True
    
    # ==========================================================================
    # Bulk Operations
    # ==========================================================================
    
    def add_recipients_bulk(
        self,
        emails: List[str],
        report_type_code: str,
        is_cc: bool = False,
        is_bcc: bool = False
    ) -> List[ReportRecipient]:
        """
        Add multiple recipients at once.
        
        Args:
            emails: List of email addresses
            report_type_code: Report type code for all recipients
            is_cc: Whether these are CC recipients
            is_bcc: Whether these are BCC recipients
            
        Returns:
            List of created/existing ReportRecipient objects
        """
        recipients = []
        for email in emails:
            recipient = self.add_recipient(
                email=email.strip(),
                report_type_code=report_type_code,
                is_cc=is_cc,
                is_bcc=is_bcc
            )
            if recipient:
                recipients.append(recipient)
        
        return recipients
    
    # ==========================================================================
    # Convenience Methods
    # ==========================================================================
    
    def ensure_report_type(
        self,
        code: str,
        name: str,
        description: Optional[str] = None
    ) -> ReportType:
        """
        Ensure a report type exists, creating it if necessary.
        Useful for initialization/seeding.
        
        Args:
            code: Unique code identifier
            name: Display name
            description: Optional description
            
        Returns:
            Existing or newly created ReportType
        """
        existing = self.get_report_type_by_code(code)
        if existing:
            return existing
        return self.create_report_type(code, name, description)
