from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session
from database.session import get_db
from common.recipient_service import RecipientService
from common.file_service import FileService
from common.pagination import create_paginated_response
from middleware.auth import get_current_user
from models.user import User
from schemas.admin import (
    ReportTypeCreate,
    ReportTypeUpdate,
    ReportTypeResponse,
    RecipientCreate,
    RecipientUpdate,
    RecipientResponse,
    FileResponse,
    PaginatedReportTypeResponse,
    PaginatedRecipientResponse,
    PaginatedFileResponse,
)
from schemas.common import MessageResponse


router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_user)])


# =============================================================================
# Report Type Endpoints
# =============================================================================

@router.get("/report-types", response_model=PaginatedReportTypeResponse)
def list_report_types(
    active_only: bool = Query(True, description="Filter to active report types only"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(5, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """List all report types with pagination."""
    service = RecipientService(db)
    
    offset = (page - 1) * page_size
    items = service.get_all_report_types(active_only=active_only, limit=page_size, offset=offset)
    total = service.count_report_types(active_only=active_only)
    
    return create_paginated_response(items=items, total=total, page=page, page_size=page_size)


@router.get("/report-types/{report_type_id}", response_model=ReportTypeResponse)
def get_report_type(
    report_type_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific report type by ID."""
    service = RecipientService(db)
    report_type = service.get_report_type_by_id(report_type_id)
    if not report_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report type with ID {report_type_id} not found"
        )
    return report_type


@router.post("/report-types", response_model=ReportTypeResponse, status_code=status.HTTP_201_CREATED)
def create_report_type(
    data: ReportTypeCreate,
    db: Session = Depends(get_db)
):
    """Create a new report type."""
    service = RecipientService(db)
    
    # Check if code already exists
    existing = service.get_report_type_by_code(data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report type with code '{data.code}' already exists"
        )
    
    return service.create_report_type(
        code=data.code,
        name=data.name,
        description=data.description
    )


@router.patch("/report-types/{report_type_id}", response_model=ReportTypeResponse)
def update_report_type(
    report_type_id: int,
    data: ReportTypeUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing report type."""
    service = RecipientService(db)
    
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    updated = service.update_report_type(report_type_id, **update_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report type with ID {report_type_id} not found"
        )
    return updated


@router.delete("/report-types/{report_type_id}", response_model=MessageResponse)
def delete_report_type(
    report_type_id: int,
    db: Session = Depends(get_db)
):
    """Delete a report type and all its recipients (cascade)."""
    service = RecipientService(db)
    
    success = service.delete_report_type(report_type_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report type with ID {report_type_id} not found"
        )
    return MessageResponse(message=f"Report type {report_type_id} deleted successfully")


# =============================================================================
# Recipient Endpoints
# =============================================================================

@router.get("/recipients", response_model=PaginatedRecipientResponse)
def list_recipients(
    report_type_code: Optional[str] = Query(None, description="Filter by report type code"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(5, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """List all recipients with pagination, optionally filtered by report type."""
    service = RecipientService(db)
    
    offset = (page - 1) * page_size
    recipients = service.get_all_recipients(
        report_type_code=report_type_code,
        limit=page_size,
        offset=offset
    )
    total = service.count_recipients(report_type_code=report_type_code)
    
    # Add report_type_code to each response
    items = []
    for r in recipients:
        response = RecipientResponse(
            id=r.id,
            email=r.email,
            name=r.name,
            report_type_id=r.report_type_id,
            report_type_code=r.report_type.code if r.report_type else None,
            is_active=r.is_active,
            is_cc=r.is_cc,
            is_bcc=r.is_bcc,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        items.append(response)
    
    return create_paginated_response(items=items, total=total, page=page, page_size=page_size)


@router.get("/recipients/{recipient_id}", response_model=RecipientResponse)
def get_recipient(
    recipient_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific recipient by ID."""
    service = RecipientService(db)
    recipient = service.get_recipient_by_id(recipient_id)
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipient with ID {recipient_id} not found"
        )
    
    return RecipientResponse(
        id=recipient.id,
        email=recipient.email,
        name=recipient.name,
        report_type_id=recipient.report_type_id,
        report_type_code=recipient.report_type.code if recipient.report_type else None,
        is_active=recipient.is_active,
        is_cc=recipient.is_cc,
        is_bcc=recipient.is_bcc,
        created_at=recipient.created_at,
        updated_at=recipient.updated_at
    )


@router.post("/recipients", response_model=RecipientResponse, status_code=status.HTTP_201_CREATED)
def create_recipient(
    data: RecipientCreate,
    db: Session = Depends(get_db)
):
    """Add a new recipient to a report type."""
    service = RecipientService(db)
    
    # Check report type exists
    report_type = service.get_report_type_by_code(data.report_type_code)
    if not report_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report type '{data.report_type_code}' not found"
        )
    
    # Check for duplicate
    existing = service.get_recipient_by_email_and_report(data.email, data.report_type_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Recipient '{data.email}' already exists for report type '{data.report_type_code}'"
        )
    
    recipient = service.add_recipient(
        email=data.email,
        report_type_code=data.report_type_code,
        name=data.name,
        is_cc=data.is_cc,
        is_bcc=data.is_bcc
    )
    
    return RecipientResponse(
        id=recipient.id,
        email=recipient.email,
        name=recipient.name,
        report_type_id=recipient.report_type_id,
        report_type_code=data.report_type_code,
        is_active=recipient.is_active,
        is_cc=recipient.is_cc,
        is_bcc=recipient.is_bcc,
        created_at=recipient.created_at,
        updated_at=recipient.updated_at
    )


@router.patch("/recipients/{recipient_id}", response_model=RecipientResponse)
def update_recipient(
    recipient_id: int,
    data: RecipientUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing recipient."""
    service = RecipientService(db)
    
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    updated = service.update_recipient(recipient_id, **update_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipient with ID {recipient_id} not found"
        )
    
    return RecipientResponse(
        id=updated.id,
        email=updated.email,
        name=updated.name,
        report_type_id=updated.report_type_id,
        report_type_code=updated.report_type.code if updated.report_type else None,
        is_active=updated.is_active,
        is_cc=updated.is_cc,
        is_bcc=updated.is_bcc,
        created_at=updated.created_at,
        updated_at=updated.updated_at
    )


@router.delete("/recipients/{recipient_id}", response_model=MessageResponse)
def delete_recipient(
    recipient_id: int,
    db: Session = Depends(get_db)
):
    """Delete a recipient."""
    service = RecipientService(db)
    
    success = service.delete_recipient(recipient_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipient with ID {recipient_id} not found"
        )
    return MessageResponse(message=f"Recipient {recipient_id} deleted successfully")


# =============================================================================
# File Endpoints (Read-Only for Admin)
# =============================================================================

@router.get("/files", response_model=PaginatedFileResponse)
def list_files(
    report_type_code: Optional[str] = Query(None, description="Filter by report type code"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(5, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    List report files with pagination and optional filters.
    If date range provided, filters by date range.
    Otherwise returns latest files for report type or all.
    """
    service = FileService(db)
    offset = (page - 1) * page_size
    
    if start_date and end_date:
        files = service.get_files_by_date_range(
            start_date=start_date,
            end_date=end_date,
            report_type_code=report_type_code,
            limit=page_size,
            offset=offset
        )
        total = service.count_files_by_date_range(
            start_date=start_date,
            end_date=end_date,
            report_type_code=report_type_code
        )
    elif report_type_code:
        files = service.get_files_by_report_type(
            report_type_code=report_type_code,
            limit=page_size,
            offset=offset
        )
        total = service.count_files_by_report_type(report_type_code)
    else:
        # Get all recent files (newest first)
        files = service.get_recent_files(limit=page_size, offset=offset)
        total = service.get_file_count()
    
    return create_paginated_response(items=files, total=total, page=page, page_size=page_size)


@router.get("/files/{file_id}", response_model=FileResponse)
def get_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific file by ID."""
    service = FileService(db)
    file = service.get_file_by_id(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} not found"
        )
    return file
