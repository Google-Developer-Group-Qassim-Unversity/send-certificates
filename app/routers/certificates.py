import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.models.schemas import (
    CertificateRequest,
    JobResponse,
    JobProgress,
    JobType,
    JobStatus,
)
from app.db.session import get_session
from app.db.schema import EmailServiceJobType
from app.services.database import DatabaseService
from app.services.certificate import process_certificates_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create certificate job",
    description="Create a new certificate generation job for multiple members",
)
async def create_certificates(
    request: CertificateRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    db = DatabaseService(session)

    event = db.get_event(request.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {request.event_id} not found",
        )

    members = db.get_members(request.member_ids)
    found_ids = {m.id for m in members}
    missing_ids = set(request.member_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Members not found: {list(missing_ids)}",
        )

    if db.is_event_processing(request.event_id):
        active_job = db.get_active_job_for_event(request.event_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Event '{event.name}' is already being processed (job_id: {active_job.id}). Please wait until it completes.",
        )

    job = db.create_job(
        event_id=request.event_id,
        member_ids=request.member_ids,
        job_type=EmailServiceJobType.CERTIFICATE,
    )

    background_tasks.add_task(
        process_certificates_job,
        job_id=job.id,
        event_id=request.event_id,
        member_ids=request.member_ids,
    )

    logger.info(
        f"Created job {job.id} for event '{event.name}' with {len(request.member_ids)} members"
    )

    return JobResponse(
        job_id=job.id,
        event_id=job.event_id,
        event_name=event.name,
        job_type=JobType.certificate,
        status=JobStatus.pending,
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
    "/{job_id}/{member_id}",
    summary="Download certificate",
    description="Download a generated PDF certificate for a specific member",
)
async def download_certificate(
    job_id: str,
    member_id: int,
    session: Session = Depends(get_session),
):
    db = DatabaseService(session)

    job = db.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )

    file_path = db.get_certificate_path_from_db(job_id, member_id)

    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate for member {member_id} in job {job_id} not found",
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=file_path.name,
    )
