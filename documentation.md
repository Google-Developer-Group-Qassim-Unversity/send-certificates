# Architecture Overview

A FastAPI service that generates personalized certificates from PowerPoint templates and emails them as PDFs.

## Project Structure

```
├── main.py          # FastAPI app with API endpoints
├── services.py      # Certificate generation & email logic
├── storage.py       # Job state & file management
├── models.py        # Pydantic models (request/response)
├── config.py        # Configuration & environment
├── manual.py        # Standalone script for testing
├── jobs/            # Generated certificates (production: ~/GDG-certificates)
├── certificate.pptx # Official template
└── index.html       # Email HTML template
```

## Core Components

| File | Purpose |
|------|---------|
| `main.py` | API routes, background task orchestration |
| `services.py` | PPTX manipulation, PDF conversion (LibreOffice), SMTP email |
| `storage.py` | In-memory job tracking + persistent `summary.json` files |
| `models.py` | Data validation with Pydantic |
| `config.py` | Settings loaded from `.env` |

## Main Flow

```
POST /certificates
       │
       ▼
┌─────────────────┐
│ Create job ID   │
│ Create folder   │
│ Queue bg task   │
└────────┬────────┘
         │
         ▼  (Background Task)
┌─────────────────────────────────────┐
│ For each member:                    │
│   1. Replace placeholders in PPTX   │
│   2. Convert PPTX → PDF (LibreOffice)│
│   3. Email PDF via SMTP             │
│   4. Update progress                │
└─────────────────────────────────────┘
         │
         ▼
   Write summary.json
```

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /certificates` | Create certificate job (async) |
| `POST /certificates/test` | Same but adds test recipients |
| `GET /status/{job_id}` | Real-time job progress |
| `GET /summary/{folder}` | Final results per member |
| `GET /summaries` | List all past jobs |
| `GET /health` | Check LibreOffice + SMTP status |

## Key Data Flows

### Request → Job
1. `CertificateRequest` → validated by Pydantic
2. Job folder created: `{event-name}-{timestamp}/`
3. Job tracked in `StorageManager._job_status` (in-memory)
4. Background task queued via FastAPI `BackgroundTasks`

### Processing Pipeline (per member)
1. `replace_placeholder()` - Opens PPTX, replaces `<<name>>`, `<<event_name>>`, `<<event_date>>`
2. `pptx_to_pdf()` - Calls LibreOffice headless
3. `send_email()` - SMTP with retry logic (3 attempts, 4s delay)
4. Status updated in memory + `summary.json` written after each member

### Storage
- **In-memory**: `_job_status` dict for real-time progress tracking
- **On-disk**: Each job folder contains:
  - `{name}-output-certificate.pptx`
  - `{name}-output-certificate.pdf`
  - `summary.json` (complete job state)

## Dependencies

- **python-pptx**: PPTX template manipulation
- **LibreOffice**: PPTX → PDF conversion (external binary)
- **smtplib**: Email sending (Gmail SMTP)

## Testing

Run `manual.py` to send test certificates without starting the server:
```python
python manual.py
```

Or use the `/certificates/test` endpoint which injects test recipients.
