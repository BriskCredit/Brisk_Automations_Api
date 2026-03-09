# Brisk Automations

Backend API for Brisk Automations - a FastAPI application for automated report generation, job posting management, and application tracking with AI-powered resume analysis.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [API Endpoints](#api-endpoints)
- [Data Schemas](#data-schemas)
- [Deployment](#deployment)

## Features

- **Authentication**: JWT-based authentication with invite-only registration system
- **Job Management**: Full CRUD for job postings with draft/publish/close workflow
- **Application Tracking**: Resume uploads, AI-powered analysis, and application status management
- **Automated Reports**: Scheduled cron jobs for customer visit and customer calls reports
- **Email Service**: Gmail SMTP integration for sending reports and notifications
- **File Storage**: Local file storage with static file serving

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLAlchemy ORM with MySQL (production) / SQLite (development)
- **Migrations**: Alembic
- **Authentication**: JWT (PyJWT) with bcrypt password hashing
- **Task Scheduling**: APScheduler
- **Containerization**: Docker

## Project Structure

```
brisk-automations/
├── main.py                 # Application entry point
├── migrate.py              # Database migration helper
├── alembic/                # Database migrations
├── common/                 # Shared services
│   ├── data_access_service.py
│   ├── email_service.py
│   ├── file_service.py
│   ├── file_storage_service.py
│   └── recipient_service.py
├── controllers/            # API route handlers
│   ├── admin_controller.py
│   ├── admin_jobs_controller.py
│   ├── auth_controller.py
│   ├── customer_calls_controller.py
│   ├── customer_visit_controller.py
│   └── jobs_controller.py
├── database/               # Database configuration
├── middleware/             # Custom middleware
├── models/                 # SQLAlchemy models
├── modules/                # Business logic modules
│   ├── customer_calls/
│   ├── customer_visit_processor/
│   └── job_applications/
├── schemas/                # Pydantic request/response schemas
├── uploads/                # File storage directory
└── utils/                  # Utility functions
```

## Setup

### Prerequisites

- Python 3.11+
- UV package manager (recommended) or pip
- MySQL (for production) or SQLite (for development)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd brisk-automations

# Install dependencies with UV
uv sync

# Or with pip
pip install -e .
```

## Environment Variables

Create a `.env` file in the project root:

```env
# Environment
ENVIRONMENT=development  # or "production"

# Database
DATABASE_URL=sqlite:///./brisk_automations.db  # Development
# DATABASE_URL=mysql+pymysql://user:password@host/database  # Production

# External Brisk Databases (for reports)
BRISK_DEFINED_URL=mysql+pymysql://user:password@host/briskc_defined
BRISK_CORE_URL=mysql+pymysql://user:password@host/briskc_core

# JWT Authentication
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (Gmail SMTP)
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER_EMAIL=your-email@gmail.com
EMAIL_SENDER_PASSWORD=your-app-password

# CORS
CORS_ORIGIN=http://localhost:3000

# File Storage
BASE_URL=http://localhost:8000  # Base URL for file URLs
```

## Database Migrations

Migrations are managed via `migrate.py`:

```bash
# Initialize migration environment (first time setup)
python migrate.py init

# Create a new migration
python migrate.py create "description"

# Apply migrations (upgrade to latest)
python migrate.py upgrade

# Upgrade to specific revision
python migrate.py upgrade <revision>

# Rollback one migration
python migrate.py downgrade

# Show current revision
python migrate.py current

# Show migration history
python migrate.py history

# Show migration status
python migrate.py status

# Reset database (⚠️ DANGER: Deletes all data!)
python migrate.py reset
```

## Running the Application

### Development

```bash
uv run python main.py
```

The API will be available at `http://localhost:8000`

### Production (Docker)

```bash
docker compose up -d
```

## API Documentation

In development mode, interactive API documentation is available:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

> Note: API docs are disabled in production for security.

---

## API Endpoints

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

---

### Authentication (`/api/v1/auth`)

All authentication endpoints except where noted.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/auth/validate-invite/{code}` | Public | Validate an invite code |
| POST | `/auth/register` | Public | Register a new user with invite code |
| POST | `/auth/login` | Public | Login and get JWT tokens |
| POST | `/auth/refresh` | Public | Refresh access token |
| GET | `/auth/me` | 🔒 | Get current user info |
| POST | `/auth/invites` | 🔒 | Create a new invite code |
| GET | `/auth/invites` | 🔒 | List all invite codes |

---

### Admin - Report Management (`/api/v1/admin`)

All endpoints require authentication 🔒

#### Report Types

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/report-types` | List all report types (paginated) |
| GET | `/admin/report-types/{code}` | Get report type by code |
| POST | `/admin/report-types` | Create a new report type |
| PATCH | `/admin/report-types/{code}` | Update a report type |
| DELETE | `/admin/report-types/{code}` | Delete a report type |

#### Recipients

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/recipients` | List recipients (paginated, filterable) |
| GET | `/admin/recipients/{id}` | Get recipient by ID |
| POST | `/admin/recipients` | Create a new recipient |
| PATCH | `/admin/recipients/{id}` | Update a recipient |
| DELETE | `/admin/recipients/{id}` | Delete a recipient |

#### Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/files` | List report files (paginated, filterable) |
| GET | `/admin/files/{id}` | Get file by ID |

---

### Admin - Job Management (`/api/v1/admin/jobs`)

All endpoints require authentication 🔒

#### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/jobs` | List all jobs (paginated, filterable by status) |
| GET | `/admin/jobs/{id}` | Get job by ID |
| POST | `/admin/jobs` | Create a new job posting |
| PATCH | `/admin/jobs/{id}` | Update a job posting |
| POST | `/admin/jobs/{id}/publish` | Publish a draft job |
| POST | `/admin/jobs/{id}/close` | Close a job |
| POST | `/admin/jobs/{id}/reopen` | Reopen a closed job |
| DELETE | `/admin/jobs/{id}` | Delete a job (use `?force=true` for non-draft) |

#### Applications

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/jobs/{job_id}/applications` | List applications for a job (sorted by AI score) |
| GET | `/admin/jobs/{job_id}/applications/stats` | Get application statistics |
| GET | `/admin/jobs/applications/{id}` | Get application by ID |
| PATCH | `/admin/jobs/applications/{id}/status` | Update application status |
| DELETE | `/admin/jobs/applications/{id}` | Delete an application |
| POST | `/admin/jobs/{job_id}/applications/reject-remaining` | Bulk reject remaining applications |

---

### Public Jobs (`/api/v1/jobs`)

All endpoints are public (no authentication required).

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/jobs` | List published (active) jobs |
| GET | `/jobs/{id}` | Get job details |
| POST | `/jobs/{id}/apply` | Submit application with resume |
| GET | `/jobs/{id}/check-application` | Check if email already applied |

---

### Customer Visit Reports (`/api/v1/customer-visit`)

All endpoints require authentication 🔒

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/customer-visit/status` | Get report status and schedule |
| GET | `/customer-visit/preview` | Preview report data without sending |
| POST | `/customer-visit/run` | Manually run the report |
| POST | `/customer-visit/toggle` | Toggle report enabled/disabled |

---

### Customer Calls Reports (`/api/v1/customer-calls`)

All endpoints require authentication 🔒

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/customer-calls/status` | Get report status and schedule |
| GET | `/customer-calls/preview` | Preview report data without sending |
| POST | `/customer-calls/run` | Manually run the report |
| POST | `/customer-calls/toggle` | Toggle report enabled/disabled |

---

## Data Schemas

### Authentication Schemas

#### RegisterRequest
```json
{
  "email": "string (required)",
  "password": "string (required, min 8 chars)",
  "name": "string (required)",
  "invite_code": "string (required)"
}
```

#### LoginRequest
```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```

#### RefreshRequest
```json
{
  "refresh_token": "string (required)"
}
```

#### TokenResponse
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### UserResponse
```json
{
  "id": 1,
  "email": "string",
  "name": "string",
  "created_at": "2026-03-04T10:00:00Z"
}
```

#### InviteResponse
```json
{
  "id": 1,
  "code": "string",
  "email": "string (optional)",
  "created_by_id": 1,
  "used": false,
  "used_by_id": null,
  "expires_at": "2026-03-11T10:00:00Z",
  "created_at": "2026-03-04T10:00:00Z"
}
```

#### CreateInviteRequest
```json
{
  "email": "string (optional - restrict invite to specific email)"
}
```

#### ValidateInviteResponse
```json
{
  "valid": true,
  "email": "string (optional)",
  "message": "Invite code is valid"
}
```

---

### Job Schemas

#### JobCreate
```json
{
  "title": "string (required)",
  "summary": "string (optional)",
  "responsibilities": "string (optional)",
  "requirements": "string (optional)",
  "qualifications": "string (optional)",
  "benefits": "string (optional)",
  "notes": "string (optional - internal)",
  "custom_instructions": "string (optional - AI analysis instructions)",
  "location": "string (optional)",
  "department": "string (optional)",
  "employment_type": "string (optional - e.g., full-time, contract)",
  "expires_at": "2026-04-04T10:00:00Z (optional)"
}
```

#### JobUpdate
```json
{
  "title": "string (optional)",
  "summary": "string (optional)",
  "responsibilities": "string (optional)",
  "requirements": "string (optional)",
  "qualifications": "string (optional)",
  "benefits": "string (optional)",
  "notes": "string (optional)",
  "custom_instructions": "string (optional)",
  "location": "string (optional)",
  "department": "string (optional)",
  "employment_type": "string (optional)",
  "expires_at": "datetime (optional)"
}
```

#### JobResponse (Admin)
```json
{
  "id": 1,
  "title": "Software Engineer",
  "summary": "string",
  "responsibilities": "string",
  "requirements": "string",
  "qualifications": "string",
  "benefits": "string",
  "notes": "string",
  "custom_instructions": "string",
  "status": "draft | published | closed",
  "location": "Nairobi, Kenya",
  "department": "Engineering",
  "employment_type": "full-time",
  "created_at": "2026-03-04T10:00:00Z",
  "updated_at": "2026-03-04T10:00:00Z",
  "published_at": "2026-03-04T12:00:00Z",
  "closed_at": null,
  "expires_at": "2026-04-04T10:00:00Z",
  "application_count": 15
}
```

#### PublicJobResponse
```json
{
  "id": 1,
  "title": "Software Engineer",
  "summary": "string",
  "responsibilities": "string",
  "requirements": "string",
  "qualifications": "string",
  "benefits": "string",
  "location": "Nairobi, Kenya",
  "department": "Engineering",
  "employment_type": "full-time",
  "published_at": "2026-03-04T12:00:00Z",
  "expires_at": "2026-04-04T10:00:00Z"
}
```

---

### Application Schemas

#### ApplicationCreate (multipart/form-data)
```
applicant_name: string (required)
applicant_email: string (required)
applicant_phone: string (optional)
cover_letter: string (optional)
resume: file (required, PDF only)
```

#### ApplicationResponse
```json
{
  "id": 1,
  "job_id": 1,
  "applicant_name": "John Doe",
  "applicant_email": "john@example.com",
  "applicant_phone": "+254700000000",
  "cover_letter": "string",
  "resume_filename": "john_doe_resume.pdf",
  "resume_url": "/files/resumes/1/2026/03/john_doe_resume.pdf",
  "ai_score": 8.5,
  "ai_comments": "Strong candidate with relevant experience...",
  "ai_analysis_status": "pending | processing | completed | failed",
  "ai_analysis_error": null,
  "status": "submitted | reviewed | shortlisted | contacted | rejected | hired",
  "admin_notes": "string",
  "created_at": "2026-03-04T10:00:00Z",
  "updated_at": "2026-03-04T10:00:00Z",
  "reviewed_at": null
}
```

#### ApplicationStatusUpdate
```json
{
  "status": "submitted | reviewed | shortlisted | contacted | rejected | hired",
  "admin_notes": "string (optional)"
}
```

#### BulkRejectRequest
```json
{
  "admin_notes": "string (optional)"
}
```

#### BulkRejectResponse
```json
{
  "success": true,
  "rejected_count": 10,
  "message": "Rejected 10 application(s)"
}
```

#### JobStatsResponse
```json
{
  "total_applications": 50,
  "by_status": {
    "submitted": 20,
    "reviewed": 15,
    "shortlisted": 10,
    "rejected": 5
  },
  "by_ai_status": {
    "completed": 45,
    "pending": 5
  },
  "average_ai_score": 6.7
}
```

---

### Admin Schemas

#### ReportTypeCreate
```json
{
  "code": "customer_visit (required, unique)",
  "name": "Customer Visit Report",
  "description": "string (optional)",
  "is_active": true
}
```

#### ReportTypeUpdate
```json
{
  "name": "string (optional)",
  "description": "string (optional)",
  "is_active": "boolean (optional)"
}
```

#### ReportTypeResponse
```json
{
  "id": 1,
  "code": "customer_visit",
  "name": "Customer Visit Report",
  "description": "string",
  "is_active": true,
  "created_at": "2026-03-04T10:00:00Z",
  "updated_at": "2026-03-04T10:00:00Z"
}
```

#### RecipientCreate
```json
{
  "email": "recipient@example.com (required)",
  "name": "John Doe (optional)",
  "report_type_code": "customer_visit (required)",
  "is_cc": false,
  "is_bcc": false
}
```

#### RecipientUpdate
```json
{
  "email": "string (optional)",
  "name": "string (optional)",
  "is_active": "boolean (optional)",
  "is_cc": "boolean (optional)",
  "is_bcc": "boolean (optional)"
}
```

#### RecipientResponse
```json
{
  "id": 1,
  "email": "recipient@example.com",
  "name": "John Doe",
  "report_type_id": 1,
  "report_type_code": "customer_visit",
  "is_active": true,
  "is_cc": false,
  "is_bcc": false,
  "created_at": "2026-03-04T10:00:00Z",
  "updated_at": "2026-03-04T10:00:00Z"
}
```

#### FileResponse
```json
{
  "id": 1,
  "report_type_id": 1,
  "filename": "customer_visit_2026-03-04.xlsx",
  "file_path": "/files/reports/customer_visit/2026/03/report.xlsx",
  "file_url": "/files/reports/customer_visit/2026/03/report.xlsx",
  "file_size": 15234,
  "report_date": "2026-03-04",
  "created_at": "2026-03-04T19:30:00Z"
}
```

---

### Report Schemas

#### RunRequest
```json
{
  "send_email": true,
  "force": false
}
```

#### RunResponse
```json
{
  "success": true,
  "message": "Report generated and sent successfully",
  "report_date": "2026-03-04",
  "records_count": 150,
  "file_url": "/files/reports/customer_visit/2026/03/report.xlsx"
}
```

#### StatusResponse
```json
{
  "report_type": "customer_visit",
  "is_enabled": true,
  "schedule": "Daily at 7:30 PM EAT",
  "last_run": "2026-03-03T19:30:00Z",
  "next_run": "2026-03-04T19:30:00Z"
}
```

#### PreviewResponse
```json
{
  "report_type": "customer_visit",
  "report_date": "2026-03-04",
  "records_count": 150,
  "preview_data": [
    { "column1": "value1", "column2": "value2" }
  ]
}
```

---

### Pagination

All list endpoints return paginated responses:

```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "page_size": 10,
  "total_pages": 10
}
```

Query parameters:
- `page` (default: 1)
- `page_size` (default: 5, max: 100)

---

## Deployment

### Docker

```bash
# Build and run
docker compose up -d

# View logs
docker compose logs -f

# Rebuild after changes
docker compose up -d --build
```

### Manual Deployment

1. Set up MySQL database
2. Configure environment variables
3. Run database migrations: `python migrate.py upgrade`
4. Run with gunicorn: `gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker`

### Cron Jobs

The application runs two scheduled jobs:

| Job | Schedule | Description |
|-----|----------|-------------|
| Customer Visit Report | Daily 7:30 PM EAT | Generates and emails visit reports |
| Customer Calls Report | Daily 7:00 PM EAT | Generates and emails call reports |

---

## License

Proprietary - Brisk Solutions
