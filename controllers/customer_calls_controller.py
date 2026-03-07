from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import EmailStr
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database.session import get_db
from common.recipient_service import RecipientService
from container.dependencies import get_brisk_data_service, get_customer_calls_cron
from modules.customer_calls.service import CustomerCallsProcessor
from modules.customer_calls.cron import REPORT_TYPE_CODE, REPORT_TYPE_NAME
from middleware.auth import get_current_user
from models.user import User
from schemas.reports import RunRequest, RunResponse, StatusResponse, PreviewResponse


router = APIRouter(prefix="/customer-calls", tags=["Customer Calls"], dependencies=[Depends(get_current_user)])


# =============================================================================
# Endpoints
# =============================================================================
# Endpoints
# =============================================================================

@router.get("/status", response_model=StatusResponse)
def get_status(db: Session = Depends(get_db)):
    """
    Get the status of customer calls report type including recipients.
    """
    service = RecipientService(db)
    
    report_type = service.get_report_type_by_code(REPORT_TYPE_CODE)
    
    if not report_type:
        return StatusResponse(
            report_type_code=REPORT_TYPE_CODE,
            report_type_name=REPORT_TYPE_NAME,
            is_active=False,
            recipient_count=0,
            recipients=[]
        )
    
    recipients_data = service.get_recipients_for_report(REPORT_TYPE_CODE)
    all_recipients = []
    
    for email in recipients_data.get("to", []):
        all_recipients.append({"email": email, "type": "to"})
    for email in recipients_data.get("cc", []):
        all_recipients.append({"email": email, "type": "cc"})
    for email in recipients_data.get("bcc", []):
        all_recipients.append({"email": email, "type": "bcc"})
    
    return StatusResponse(
        report_type_code=report_type.code,
        report_type_name=report_type.name,
        is_active=report_type.is_active,
        recipient_count=len(all_recipients),
        recipients=all_recipients
    )


@router.get("/preview", response_model=PreviewResponse)
def preview_report():
    """
    Generate a preview of the customer calls report without sending emails.
    Returns the summary data that would be included in the report.
    """
    try:
        data_service = get_brisk_data_service()
        processor = CustomerCallsProcessor(data_service=data_service)
        
        result = processor.process()
        
        # Convert to list of dicts for JSON response
        summary = result.to_dict(orient='records')
        
        return PreviewResponse(
            success=True,
            generated_at=datetime.now(),
            row_count=len(result),
            columns=list(result.columns),
            summary=summary
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}"
        )


@router.post("/run", response_model=RunResponse)
async def run_manually(
    request: Optional[RunRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Manually trigger the customer calls cron job.
    
    Optionally provide override_recipients to send to specific emails instead of DB recipients.
    """
    service = RecipientService(db)
    report_type = service.get_report_type_by_code(REPORT_TYPE_CODE)
    
    if report_type and not report_type.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report type '{REPORT_TYPE_CODE}' is inactive. Enable it first."
        )
    
    try:
        override_recipients = request.override_recipients if request else None
        
        with get_customer_calls_cron() as cron:
            result = await cron.process(override_recipients=override_recipients)
        
        return RunResponse(
            success=True,
            message="Customer calls report generated and sent successfully",
            rows=len(result) if result is not None else 0
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run customer calls job: {str(e)}"
        )


@router.post("/toggle", response_model=StatusResponse)
def toggle_active(
    is_active: bool = Query(..., description="Set the active status"),
    db: Session = Depends(get_db)
):
    """
    Enable or disable the customer calls report type.
    """
    service = RecipientService(db)
    
    report_type = service.get_report_type_by_code(REPORT_TYPE_CODE)
    
    if not report_type:
        # Create report type if it doesn't exist
        report_type = service.create_report_type(
            code=REPORT_TYPE_CODE,
            name=REPORT_TYPE_NAME,
            description="Call dialer tracking report for D7, D30, DD+30, and DD+60 intervals"
        )
    
    # Update active status
    updated = service.update_report_type(report_type.id, is_active=is_active)
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update report type status"
        )
    
    recipients_data = service.get_recipients_for_report(REPORT_TYPE_CODE)
    all_recipients = []
    
    for email in recipients_data.get("to", []):
        all_recipients.append({"email": email, "type": "to"})
    for email in recipients_data.get("cc", []):
        all_recipients.append({"email": email, "type": "cc"})
    for email in recipients_data.get("bcc", []):
        all_recipients.append({"email": email, "type": "bcc"})
    
    return StatusResponse(
        report_type_code=updated.code,
        report_type_name=updated.name,
        is_active=updated.is_active,
        recipient_count=len(all_recipients),
        recipients=all_recipients
    )
