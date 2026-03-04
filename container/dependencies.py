from contextlib import contextmanager
from typing import Generator
from database.brisk_engines import brisk_engines
from database.session import SessionLocal
from common.brisk_data_service import BriskDataService
from common.email_service import EmailService
from common.recipient_service import RecipientService
from common.file_storage_service import FileStorageService
from common.file_service import FileService
from modules.customer_visit_processor.cron import CustomerVisitProcessorCron
from modules.customer_calls.cron import CustomerCallsCron


# ============================================================================
# Shared Service Providers
# ============================================================================

def get_brisk_data_service() -> BriskDataService:
    """
    Create and return a BriskDataService instance.
    Uses the singleton brisk_engines for database connections.
    
    Returns:
        BriskDataService configured with main and core engines
    """
    return BriskDataService(
        main_engine=brisk_engines.main_engine,
        core_engine=brisk_engines.core_engine
    )


def get_email_service() -> EmailService:
    """
    Create and return an EmailService instance.
    Uses GMAIL_EMAIL and GMAIL_APP_PASSWORD from environment.
    
    Returns:
        EmailService configured with Gmail credentials
    """
    return EmailService()


@contextmanager
def get_recipient_service() -> Generator[RecipientService, None, None]:
    """
    Context manager that provides RecipientService with database session.
    Automatically handles session lifecycle.
    
    Yields:
        RecipientService instance
    """
    db = SessionLocal()
    try:
        yield RecipientService(db)
    finally:
        db.close()


def get_file_storage_service() -> FileStorageService:
    """
    Create and return a FileStorageService instance.
    Uses BASE_URL from environment for URL generation.
    
    Returns:
        FileStorageService configured for file operations
    """
    return FileStorageService()


@contextmanager
def get_file_service() -> Generator[FileService, None, None]:
    """
    Context manager that provides FileService with database session.
    Automatically handles session lifecycle.
    
    Yields:
        FileService instance
    """
    db = SessionLocal()
    try:
        yield FileService(db)
    finally:
        db.close()


# ============================================================================
# Cron Job Dependency Providers (for use outside FastAPI request context)
# ============================================================================

@contextmanager
def get_customer_visit_processor_cron() -> Generator[CustomerVisitProcessorCron, None, None]:
    """
    Context manager that provides CustomerVisitProcessorCron with proper dependency injection.
    Injects BriskDataService, EmailService, RecipientService, FileStorageService, and FileService.
    
    Usage:
        with get_customer_visit_processor_cron() as cron:
            await cron.process()
    
    Yields:
        CustomerVisitProcessorCron instance with injected dependencies
    """
    data_service = get_brisk_data_service()
    email_service = get_email_service()
    file_storage_service = get_file_storage_service()
    
    with get_recipient_service() as recipient_service:
        with get_file_service() as file_service:
            cron = CustomerVisitProcessorCron(
                data_service=data_service,
                email_service=email_service,
                recipient_service=recipient_service,
                file_storage_service=file_storage_service,
                file_service=file_service
            )
            yield cron


@contextmanager
def get_customer_calls_cron() -> Generator[CustomerCallsCron, None, None]:
    """
    Context manager that provides CustomerCallsCron with proper dependency injection.
    Injects BriskDataService, EmailService, RecipientService, FileStorageService, and FileService.
    
    Usage:
        with get_customer_calls_cron() as cron:
            await cron.process()
    
    Yields:
        CustomerCallsCron instance with injected dependencies
    """
    data_service = get_brisk_data_service()
    email_service = get_email_service()
    file_storage_service = get_file_storage_service()
    
    with get_recipient_service() as recipient_service:
        with get_file_service() as file_service:
            cron = CustomerCallsCron(
                data_service=data_service,
                email_service=email_service,
                recipient_service=recipient_service,
                file_storage_service=file_storage_service,
                file_service=file_service
            )
            yield cron
