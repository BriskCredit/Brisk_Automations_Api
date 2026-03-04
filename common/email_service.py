import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from pathlib import Path
from utils.logger import get_logger

logger = get_logger("app.common.email")


class EmailService:
    """
    Email service for sending emails via Gmail SMTP with app password.
    Supports multiple recipients and file attachments.
    """
    
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    
    def __init__(self, sender_email: Optional[str] = None, app_password: Optional[str] = None):
        """
        Initialize email service with Gmail credentials.
        
        Args:
            sender_email: Gmail address (defaults to GMAIL_EMAIL env var)
            app_password: Gmail app password (defaults to GMAIL_APP_PASSWORD env var)
        """
        self.sender_email = sender_email or os.getenv("GMAIL_EMAIL")
        self.app_password = app_password or os.getenv("GMAIL_APP_PASSWORD")
        
        if not self.sender_email or not self.app_password:
            raise ValueError(
                "Gmail credentials not configured. "
                "Set GMAIL_EMAIL and GMAIL_APP_PASSWORD environment variables."
            )
    
    def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email to multiple recipients with optional attachments.
        
        Args:
            to: List of recipient email addresses
            subject: Email subject line
            body: Plain text email body
            attachments: Optional list of file paths to attach
            html_body: Optional HTML version of the email body
            cc: Optional list of CC recipients
            bcc: Optional list of BCC recipients
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative" if html_body else "mixed")
            msg["From"] = self.sender_email
            msg["To"] = ", ".join(to)
            msg["Subject"] = subject
            
            if cc:
                msg["Cc"] = ", ".join(cc)
            
            # Attach plain text body
            msg.attach(MIMEText(body, "plain"))
            
            # Attach HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, "html"))
            
            # Attach files
            if attachments:
                for file_path in attachments:
                    self._attach_file(msg, file_path)
            
            # Build recipient list (to + cc + bcc)
            all_recipients = list(to)
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)
            
            # Send email
            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, all_recipients, msg.as_string())
            
            logger.info(f"Email sent successfully to {len(all_recipients)} recipient(s): {subject}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _attach_file(self, msg: MIMEMultipart, file_path: str) -> None:
        """
        Attach a file to the email message.
        
        Args:
            msg: The email message to attach to
            file_path: Path to the file to attach
        """
        path = Path(file_path)
        
        if not path.exists():
            logger.warning(f"Attachment file not found: {file_path}")
            return
        
        with open(path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={path.name}"
        )
        msg.attach(part)
        logger.debug(f"Attached file: {path.name}")
    
    def send_report_email(
        self,
        to: List[str],
        report_path: str,
        report_name: str = "Report",
        additional_message: str = ""
    ) -> bool:
        """
        Convenience method for sending report emails with standard formatting.
        
        Args:
            to: List of recipient email addresses
            report_path: Path to the report file to attach
            report_name: Name of the report for the email subject/body
            additional_message: Optional additional message to include
            
        Returns:
            True if email sent successfully
        """
        from datetime import datetime
        
        today = datetime.now().strftime("%B %d, %Y")
        subject = f"{report_name} - {today}"
        
        body = f"""Hello,

Please find attached the {report_name} for {today}.

{additional_message}

This is an automated email from Brisk Automations.

Best regards,
Brisk Automations System
"""
        
        return self.send_email(
            to=to,
            subject=subject,
            body=body,
            attachments=[report_path]
        )
