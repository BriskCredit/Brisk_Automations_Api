# Schemas Package
from schemas.common import MessageResponse, PaginatedResponse
from schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
    InviteResponse,
    CreateInviteRequest,
    ValidateInviteResponse,
)
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
from schemas.jobs import (
    JobCreate,
    JobUpdate,
    JobResponse,
    JobListResponse,
    PublicJobResponse,
    PublicJobListResponse,
    ApplicationResponse,
    ApplicationListResponse,
    ApplicationStatusUpdate,
    BulkRejectRequest,
    BulkRejectResponse,
    JobStatsResponse,
    ApplicationSubmitResponse,
)
from schemas.reports import (
    RunRequest,
    RunResponse,
    StatusResponse,
    PreviewResponse,
    PreviewSummary,
)

__all__ = [
    # Common
    "MessageResponse",
    "PaginatedResponse",
    # Auth
    "RegisterRequest",
    "LoginRequest",
    "RefreshRequest",
    "TokenResponse",
    "UserResponse",
    "InviteResponse",
    "CreateInviteRequest",
    "ValidateInviteResponse",
    # Admin
    "ReportTypeCreate",
    "ReportTypeUpdate",
    "ReportTypeResponse",
    "RecipientCreate",
    "RecipientUpdate",
    "RecipientResponse",
    "FileResponse",
    "PaginatedReportTypeResponse",
    "PaginatedRecipientResponse",
    "PaginatedFileResponse",
    # Jobs
    "JobCreate",
    "JobUpdate",
    "JobResponse",
    "JobListResponse",
    "PublicJobResponse",
    "PublicJobListResponse",
    "ApplicationResponse",
    "ApplicationListResponse",
    "ApplicationStatusUpdate",
    "BulkRejectRequest",
    "BulkRejectResponse",
    "JobStatsResponse",
    "ApplicationSubmitResponse",
    # Reports
    "RunRequest",
    "RunResponse",
    "StatusResponse",
    "PreviewResponse",
    "PreviewSummary",
]
