from typing import TYPE_CHECKING, List, Optional
from datetime import datetime
from utils.logger import get_logger
from utils.report_type_helper import ensure_report_type_active
from modules.customer_calls.service import CustomerCallsProcessor

if TYPE_CHECKING:
    from common.brisk_data_service import BriskDataService
    from common.email_service import EmailService
    from common.recipient_service import RecipientService
    from common.file_storage_service import FileStorageService
    from common.file_service import FileService

logger = get_logger("app.cron.customer_calls")

# Report type configuration for this module
REPORT_TYPE_CODE = "customer_calls"
REPORT_TYPE_NAME = "Call Dialer Report"
REPORT_TYPE_DESCRIPTION = "Call dialer tracking report for D7, D30, DD+30, and DD+60 intervals"


class CustomerCallsCron:
    """
    Cron job handler for Customer Calls processing tasks.
    Uses dependency injection for all services.
    """
    
    def __init__(
        self, 
        data_service: "BriskDataService",
        email_service: "EmailService",
        recipient_service: "RecipientService",
        file_storage_service: "FileStorageService",
        file_service: "FileService"
    ):
        """
        Initialize cron handler with required dependencies.
        
        Args:
            data_service: BriskDataService for database access
            email_service: EmailService for sending reports via email
            recipient_service: RecipientService for fetching email recipients from DB
            file_storage_service: FileStorageService for saving files to disk
            file_service: FileService for recording files in database
        """
        self._data_service = data_service
        self._email_service = email_service
        self._recipient_service = recipient_service
        self._file_storage_service = file_storage_service
        self._file_service = file_service
        self.logger = logger
        self.report_type_id: Optional[int] = None

    async def process(self, override_recipients: Optional[List[str]] = None):
        """
        Cron job to process call dialer data.
        Generates report and sends via email.
        
        Args:
            override_recipients: Optional list to override DB recipients (for testing).
        """
        self.logger.info("Starting Call Dialer processing cron job...")
        
        # Ensure report type exists and is active
        report_type_id, is_active = ensure_report_type_active(
            self._recipient_service,
            code=REPORT_TYPE_CODE,
            name=REPORT_TYPE_NAME,
            description=REPORT_TYPE_DESCRIPTION
        )
        
        if not is_active:
            self.logger.info(f"Report type '{REPORT_TYPE_CODE}' is inactive. Skipping execution.")
            return None
        
        self.report_type_id = report_type_id
        
        try:
            processor = CustomerCallsProcessor(data_service=self._data_service)
            
            result = processor.process()
            self.logger.info(f"Call Dialer processing completed. Report shape: {result.shape}")
            
            # Export to Excel
            filepath = processor.to_excel()
            self.logger.info(f"Report exported to: {filepath}")
            
            # Get recipients from database
            if override_recipients:
                recipients = {"to": override_recipients, "cc": [], "bcc": []}
            else:
                recipients = self._recipient_service.get_recipients_for_report(REPORT_TYPE_CODE)
            
            if recipients["to"]:
                success = self._email_service.send_email(
                    to=recipients["to"],
                    cc=recipients["cc"] if recipients["cc"] else None,
                    bcc=recipients["bcc"] if recipients["bcc"] else None,
                    subject="Call Dialer Report",
                    body=self._generate_email_body(),
                    attachments=[filepath]
                )
                total_recipients = len(recipients["to"]) + len(recipients["cc"]) + len(recipients["bcc"])
                if success:
                    self.logger.info(f"Report emailed to {total_recipients} recipient(s)")
                else:
                    self.logger.warning("Failed to send report email")
            else:
                self.logger.warning(f"No email recipients configured for '{REPORT_TYPE_CODE}'. Skipping email.")
            
            # Save file to storage and record in database
            await self._save_report_file(filepath)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing call dialer: {e}")
            raise
    
    async def _save_report_file(self, source_filepath: str) -> None:
        """
        Save the report file to storage and record it in the database.
        
        Args:
            source_filepath: Path to the generated Excel file
        """
        try:
            report_date = datetime.now().date()
            
            # Save to storage (moves file and returns file info dict)
            file_info = self._file_storage_service.save_file(
                source_path=source_filepath,
                category="reports",
                subcategory=REPORT_TYPE_CODE,
                delete_source=True  # Clean up temp file after moving
            )
            self.logger.info(f"Report file saved to storage: {file_info['file_path']}")
            
            # Record in database
            file_record = self._file_service.create_file_record(
                filename=file_info["filename"],
                file_path=file_info["file_path"],
                file_url=file_info["file_url"],
                file_size=file_info["file_size"],
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                report_type_id=self.report_type_id,
                report_date=report_date
            )
            
            if file_record:
                self.logger.info(f"Report file recorded in database with ID: {file_record.id}")
            else:
                self.logger.warning("Failed to record file in database")
                
        except Exception as e:
            self.logger.error(f"Error saving report file: {e}")
            # Don't re-raise - file saving failure shouldn't fail the entire job
    
    def _generate_email_body(self) -> str:
        """Generate the email body for the report."""
        today = datetime.now().strftime("%B %d, %Y")
        
        return f"""Hello,

Please find attached the Call Dialer Report for {today}.

This report includes call dialer tracking data for D7, D30, DD+30, and DD+60 intervals, grouped by branch.

The report contains:
- Summary sheet with called/total statistics per branch
- Detailed sheets for accounts not yet called in each interval

This is an automated email from Brisk Automations.

Best regards,
Brisk Automations System
"""
