# Architecture Overview

A FastAPI service that generates personalized certificates from PowerPoint templates and emails them as PDFs. Also supports email blasts to multiple recipients.

## Project Structure

```
app/
├── __init__.py
├── main.py              # FastAPI app instance + router includes
├── core/
│   ├── __init__.py
│   ├── auth.py          # Clerk JWT authentication & admin guards
│   ├── config.py        # Configuration & environment settings
│   ├── error_handlers.py# Global exception handlers
│   ├── exceptions.py    # Custom exception classes
│   └── startup.py       # Startup validation checks
├── db/
│   ├── __init__.py
│   ├── schema.py        # SQLModel database models (reflected from MySQL)
│   └── session.py       # Database engine & session management
├── models/
│   ├── __init__.py
│   └── schemas.py       # Pydantic models (request/response)
├── routers/
│   ├── __init__.py
│   ├── certificates.py  # Certificate API endpoints
│   ├── email_blasts.py  # Email blast API endpoints
│   └── status.py        # Job status, health check, list endpoints
└── services/
    ├── __init__.py
    ├── certificate.py   # Certificate generation & email logic
    ├── database.py      # Database operations wrapper
    └── email_blast.py   # Email blast processing logic

alembic/                 # Database migrations
├── env.py
└── versions/

├── certificate.pptx         # Official template
├── certificate unofficial.pptx  # Unofficial template
└── index.html               # Email HTML template
```

## Core Components

| File                            | Purpose                                                            |
| ------------------------------- | ------------------------------------------------------------------ |
| `app/main.py`                 | FastAPI app instance, lifespan events, router registration         |
| `app/routers/certificates.py` | Certificate API routes, background task orchestration              |
| `app/routers/email_blasts.py` | Email blast API routes                                             |
| `app/routers/status.py`       | Job listing, status, health check endpoints                        |
| `app/services/certificate.py` | PPTX manipulation, PDF conversion (LibreOffice), SMTP email        |
| `app/services/database.py`    | Database operations for jobs, recipients, certificates             |
| `app/services/email_blast.py` | Email blast sending via SMTP                                       |
| `app/models/schemas.py`       | Data validation with Pydantic                                      |
| `app/db/schema.py`            | SQLModel ORM models (existing MySQL schema + email service tables) |
| `app/core/config.py`          | Settings loaded from `.env`                                      |
| `app/core/auth.py`            | Clerk JWT authentication, admin role verification                  |
| `app/core/exceptions.py`      | Custom exception hierarchy                                         |
| `app/core/startup.py`         | Validation checks on app startup                                   |

## Authentication

All API endpoints require authentication via **Clerk JWT**. The `admin_guard` dependency validates:

1. Valid JWT token from Clerk
2. User has `is_admin` or `is_super_admin` metadata set

## Job Types

| Type                   | Description                                |
| ---------------------- | ------------------------------------------ |
| `certificate_event`  | Certificates for event members (DB lookup) |
| `certificate_custom` | Certificates for custom recipients (no DB) |
| `email_blast`        | Single email sent to multiple recipients   |
| `reminder`           | (Reserved for future use)                  |
| `notification`       | (Reserved for future use)                  |

## Main Flow - Certificates

```
POST /certificates (event-based) or POST /certificates/custom
        │
        ▼
┌─────────────────┐
│ Validate auth   │
│ Validate input  │
│ Create job in DB│
│ Queue bg task   │
└────────┬────────┘
         │
         ▼  (Background Task)
┌─────────────────────────────────────┐
│ For each recipient:                 │
│   1. Get member data (if event)     │
│   2. Replace placeholders in PPTX   │
│   3. Convert PPTX → PDF (LibreOffice)│
│   4. Email PDF via SMTP             │
│   5. Update recipient status in DB  │
└─────────────────────────────────────┘
         │
         ▼
   Update job status to completed/failed
```

## Main Flow - Email Blasts

```
POST /email-blasts
        │
        ▼
┌─────────────────┐
│ Validate auth   │
│ Resolve members │
│ Create job in DB│
│ Queue bg task   │
└────────┬────────┘
         │
         ▼  (Background Task)
┌─────────────────────────────────────┐
│ 1. Build recipient list             │
│ 2. Send single email to all (BCC)   │
│ 3. Update blast status in DB        │
└─────────────────────────────────────┘
```

## API Endpoints

### Certificates

| Endpoint                                            | Purpose                                      |
| --------------------------------------------------- | -------------------------------------------- |
| `POST /certificates`                              | Create certificate job for event members     |
| `POST /certificates/custom`                       | Create certificate job for custom recipients |
| `GET /certificates/{job_id}/{member_id_or_email}` | Download generated PDF                       |

### Email Blasts

| Endpoint                       | Purpose                   |
| ------------------------------ | ------------------------- |
| `POST /email-blasts`         | Create email blast job    |
| `GET /email-blasts`          | List all email blast jobs |
| `GET /email-blasts/{job_id}` | Get email blast details   |

### Jobs & Status

| Endpoint                          | Purpose                               |
| --------------------------------- | ------------------------------------- |
| `GET /jobs`                     | List all jobs (paginated, filterable) |
| `GET /jobs/{job_id}`            | Get job status                        |
| `GET /jobs/{job_id}/recipients` | Get job recipients with status        |
| `GET /health`                   | Check LibreOffice + SMTP status       |
| `GET /startup-status`           | Get startup validation results        |

## Database Schema (Email Service Tables)

| Table                          | Purpose                                     |
| ------------------------------ | ------------------------------------------- |
| `email_service_jobs`         | Job tracking (type, status, progress)       |
| `email_service_recipients`   | Per-recipient status and metadata           |
| `email_service_certificates` | Certificate file paths linked to recipients |
| `email_service_email_blasts` | Email blast content and delivery status     |

The service also reads from existing tables: `events`, `members`, `forms`, `submissions`, etc.

## Key Data Flows

### Request → Job (Event Certificates)

1. `CertificateRequest` validated by Pydantic in `app/models/schemas.py`
2. Event fetched from database, checked for active jobs
3. Members validated against database
4. Job created in `email_service_jobs` with recipients in `email_service_recipients`
5. Background task queued via FastAPI `BackgroundTasks`

### Processing Pipeline (per recipient)

1. `replace_placeholder()` - Opens PPTX, replaces `<<name>>`, `<<event_name>>`, `<<event_date>>`
2. `pptx_to_pdf()` - Calls LibreOffice headless
3. `send_email()` - SMTP with retry logic (3 attempts, 4s delay)
4. Status updated in `email_service_recipients` table

All implemented in `app/services/certificate.py`.

### Storage

- **Database**: Job state, recipient status, certificate paths
- **Filesystem**: Generated PDFs stored in `{certificates_folder}/{event_id}-{event_name}/` or `custom-{job_id}/`

## Dependencies

- **python-pptx**: PPTX template manipulation
- **LibreOffice**: PPTX → PDF conversion (external binary)
- **smtplib**: Email sending (Gmail SMTP)
- **SQLModel/SQLAlchemy**: Database ORM
- **fastapi-clerk-auth**: Clerk JWT authentication
- **Alembic**: Database migrations

## Configuration (`.env`)

```
ENV=development|production
DATABASE_URL=mysql://user:pass@host/db
APP_PASSWORD=your_gmail_app_password
```

## Startup Validation

On startup, the app validates:

- Official/unofficial PPTX templates exist
- Email HTML template exists
- LibreOffice is available
- Certificates folder is writable
- Database connection works

Results available at `GET /startup-status`.
