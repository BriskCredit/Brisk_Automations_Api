"""
Utility for ensuring report types exist and are active for modules.
Provides a clean interface for modules to check/create their report types.
"""
from typing import Optional, Tuple
from utils.logger import get_logger

logger = get_logger("app.utils.report_type_helper")


def ensure_report_type_active(
    recipient_service,
    code: str,
    name: str,
    description: Optional[str] = None
) -> Tuple[Optional[int], bool]:
    """
    Ensure a report type exists and check if it's active.
    
    This utility handles three scenarios:
    1. Report type doesn't exist -> Create it and return (id, True)
    2. Report type exists and is_active=True -> Return (id, True)
    3. Report type exists but is_active=False -> Return (id, False)
    
    Args:
        recipient_service: RecipientService instance with active DB session
        code: Unique report type code (e.g., 'customer_visit')
        name: Display name (e.g., 'Customer Visit Report')
        description: Optional description
        
    Returns:
        Tuple of (report_type_id, is_active)
        - If active: (id, True) - proceed with report
        - If inactive: (id, False) - skip report execution
        - If error: (None, False) - skip report execution
        
    Example:
        report_type_id, is_active = ensure_report_type_active(
            recipient_service,
            code="customer_visit",
            name="Customer Visit Report",
            description="D7/D14/D21 customer visit tracking"
        )
        
        if not is_active:
            logger.info("Report type is inactive, skipping...")
            return
            
        # Continue with report generation...
    """
    try:
        # Check if report type exists
        report_type = recipient_service.get_report_type_by_code(code)
        
        if report_type:
            # Exists - check if active
            if report_type.is_active:
                logger.debug(f"Report type '{code}' is active (id={report_type.id})")
                return (report_type.id, True)
            else:
                logger.info(f"Report type '{code}' exists but is inactive, skipping execution")
                return (report_type.id, False)
        
        # Doesn't exist - create it
        logger.info(f"Creating report type '{code}'...")
        report_type = recipient_service.create_report_type(
            code=code,
            name=name,
            description=description
        )
        
        logger.info(f"Created report type '{code}' with id={report_type.id}")
        return (report_type.id, True)
        
    except Exception as e:
        logger.error(f"Error ensuring report type '{code}': {e}")
        return (None, False)
