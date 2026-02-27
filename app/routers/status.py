import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    JobStatusResponse,
    JobProgress,
    JobSummary,
    EventsList,
    HealthCheck,
)
from app.services.storage import storage
from app.services.certificate import certificate_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["status"])


@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Get the current status of a certificate generation job",
)
async def get_job_status(job_id: str):
    job_status = storage.get_job_status(job_id)

    if not job_status:
        folder_name = storage.get_folder_by_job_id(job_id)
        if folder_name:
            summary = storage.read_summary(folder_name)
            if summary:
                return JobStatusResponse(
                    job_id=summary.job_id,
                    event_name=summary.event_name,
                    folder_name=summary.folder_name,
                    status=summary.status,
                    progress=JobProgress(
                        total=summary.total_members,
                        completed=summary.total_members,
                        successful=summary.successful,
                        failed=summary.failed,
                    ),
                    created_at=summary.created_at,
                    updated_at=summary.completed_at or summary.created_at,
                )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )

    return JobStatusResponse(
        job_id=job_status["job_id"],
        event_name=job_status["event_name"],
        folder_name=job_status["folder_name"],
        status=job_status["status"],
        progress=JobProgress(**job_status["progress"]),
        created_at=datetime.fromisoformat(job_status["created_at"]),
        updated_at=datetime.fromisoformat(job_status["updated_at"]),
    )


@router.get(
    "/summary/{folder_name}",
    response_model=JobSummary,
    summary="Get job summary",
    description="Get the complete summary of a finished job including all member results",
)
async def get_job_summary(folder_name: str):
    summary = storage.read_summary(folder_name)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary for folder '{folder_name}' not found",
        )

    return summary


@router.get(
    "/summaries",
    response_model=EventsList,
    summary="List all summaries",
    description="Get a list of all job summaries",
)
async def list_summaries():
    events = storage.list_all_summaries()

    return EventsList(
        total=len(events),
        events=events,
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
        timestamp=datetime.utcnow(),
    )
