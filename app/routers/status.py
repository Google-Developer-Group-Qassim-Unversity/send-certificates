import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.models.schemas import (
    JobResponse,
    JobDetailResponse,
    JobProgress,
    JobsListResponse,
    JobListItem,
    RecipientResult,
    HealthCheck,
    JobType,
    JobStatus,
    RecipientStatus,
)
from app.db.session import get_session
from app.db.schema import EmailServiceJobType
from app.services.database import DatabaseService
from app.services.certificate import certificate_service
from app.core.auth import admin_guard

logger = logging.getLogger(__name__)

router = APIRouter(tags=["jobs"])


@router.get(
    "/jobs",
    response_model=JobsListResponse,
    summary="List all jobs",
    description="Get a paginated list of all email service jobs",
)
async def list_jobs(
    event_id: int | None = Query(None, description="Filter by event ID"),
    job_type: JobType | None = Query(None, description="Filter by job type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    credentials=Depends(admin_guard),
):
    db = DatabaseService(session)

    db_job_type = None
    if job_type:
        db_job_type = EmailServiceJobType(job_type.value)

    jobs = db.list_jobs(
        event_id=event_id, job_type=db_job_type, limit=limit, offset=offset
    )
    total = db.count_jobs(event_id=event_id, job_type=db_job_type)

    job_items = []
    for job in jobs:
        event = db.get_event(job.event_id) if job.event_id else None
        job_items.append(
            JobListItem(
                job_id=job.id,
                event_id=job.event_id,
                event_name=event.name if event else "Unknown",
                job_type=JobType(job.job_type.value),
                status=JobStatus(job.status.value),
                progress=JobProgress(
                    total=job.total,
                    completed=job.completed,
                    successful=job.successful,
                    failed=job.failed,
                ),
                created_at=job.created_at,
            )
        )

    return JobsListResponse(total=total, jobs=job_items)


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get job status",
    description="Get the current status of an email service job",
)
async def get_job_status(
    job_id: str,
    session: Session = Depends(get_session),
    credentials=Depends(admin_guard),
):
    db = DatabaseService(session)

    job = db.get_job_or_raise(job_id)

    event = db.get_event(job.event_id) if job.event_id else None

    return JobResponse(
        job_id=job.id,
        event_id=job.event_id,
        event_name=event.name if event else "Unknown",
        job_type=JobType(job.job_type.value),
        status=JobStatus(job.status.value),
        progress=JobProgress(
            total=job.total,
            completed=job.completed,
            successful=job.successful,
            failed=job.failed,
        ),
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get(
    "/jobs/{job_id}/recipients",
    response_model=JobDetailResponse,
    summary="Get job recipients",
    description="Get the complete list of recipients and their status for a job",
)
async def get_job_recipients(
    job_id: str,
    session: Session = Depends(get_session),
    credentials=Depends(admin_guard),
):
    db = DatabaseService(session)

    job = db.get_job_or_raise(job_id)

    event = db.get_event(job.event_id) if job.event_id else None
    recipients = db.get_recipients_for_job(job_id)

    recipient_results = []
    for recipient in recipients:
        assert recipient.id, "Recipient ID should exist"
        member = db.get_member(recipient.member_id) if recipient.member_id else None
        certificate = db.get_certificate_for_recipient(recipient.id)

        certificate_url = None
        if certificate:
            certificate_url = f"/certificates/{job_id}/{recipient.member_id}"

        recipient_results.append(
            RecipientResult(
                recipient_id=recipient.id,
                member_id=recipient.member_id,
                name=member.name if member else (recipient.name or "Unknown"),
                email=member.email if member else recipient.email,
                status=RecipientStatus(recipient.status.value),
                sent_at=recipient.sent_at,
                certificate_url=certificate_url,
                error=recipient.error,
            )
        )

    return JobDetailResponse(
        job_id=job.id,
        event_id=job.event_id,
        event_name=event.name if event else "Unknown",
        job_type=JobType(job.job_type.value),
        status=JobStatus(job.status.value),
        progress=JobProgress(
            total=job.total,
            completed=job.completed,
            successful=job.successful,
            failed=job.failed,
        ),
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        recipients=recipient_results,
    )


@router.get(
    "/health",
    response_model=HealthCheck,
    summary="Health check",
    description="Check the health of the API and its dependencies",
)
async def health_check():
    libreoffice_status = (
        "available" if certificate_service.check_libreoffice() else "unavailable"
    )
    smtp_status = "configured" if certificate_service.check_smtp() else "unavailable"

    overall_status = (
        "healthy"
        if libreoffice_status == "available" and smtp_status == "configured"
        else "degraded"
    )

    return HealthCheck(
        status=overall_status,
        libreoffice=libreoffice_status,
        smtp=smtp_status,
        timestamp=datetime.now(timezone.utc),
    )
