import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.models.schemas import (
    CertificateRequest,
    CustomCertificateRequest,
    JobResponse,
    JobProgress,
    JobType,
    JobStatus,
)
from app.db.session import get_session
from app.db.schema import EmailServiceJobType
from app.services.database import DatabaseService
from app.services.certificate import (
    process_certificate_event_job,
    process_certificate_custom_job,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create certificate job",
    description="Create a new certificate generation job for event members (DB lookup)",
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

    if db.is_event_processing(request.event_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Event '{event.name}' is already being processed. Please wait until it completes.",
        )

    members = db.get_members(request.member_ids)
    found_ids = {m.id for m in members}
    missing_ids = set(request.member_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Members not found: {sorted(missing_ids)}",
        )

    job = db.create_certificate_job_for_event(
        event_id=request.event_id,
        member_ids=request.member_ids,
    )

    background_tasks.add_task(
        process_certificate_event_job,
        job_id=job.id,
    )

    logger.info(
        f"Created job {job.id} for event '{event.name}' with {len(request.member_ids)} members"
    )

    return JobResponse(
        job_id=job.id,
        event_id=job.event_id,
        event_name=event.name,
        job_type=JobType.certificate_event,
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


@router.post(
    "/custom",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create custom certificate job",
    description="Create a certificate generation job with custom recipients (not from DB)",
)
async def create_custom_certificates(
    request: CustomCertificateRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    db = DatabaseService(session)

    if request.event_id:
        event = db.get_event(request.event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {request.event_id} not found",
            )

    recipients_data = [r.model_dump() for r in request.recipients]

    job = db.create_certificate_job_custom(
        recipients=recipients_data,
        event_name=request.event_name,
        event_date=request.event_date,
        official=request.official,
        event_id=request.event_id,
    )

    background_tasks.add_task(
        process_certificate_custom_job,
        job_id=job.id,
    )

    logger.info(
        f"Created custom job {job.id} for '{request.event_name}' with {len(request.recipients)} recipients"
    )

    return JobResponse(
        job_id=job.id,
        event_id=job.event_id,
        event_name=request.event_name,
        job_type=JobType.certificate_custom,
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
    "/{job_id}/{member_id_or_email}",
    summary="Download certificate",
    description="Download a generated PDF certificate for a specific member or custom recipient",
)
async def download_certificate(
    job_id: str,
    member_id_or_email: str,
    session: Session = Depends(get_session),
):
    db = DatabaseService(session)

    job = db.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )

    file_path = None

    if job.job_type == EmailServiceJobType.CERTIFICATE_EVENT:
        try:
            member_id = int(member_id_or_email)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For certificate_event jobs, member_id must be an integer",
            )
        file_path = db.get_certificate_path_from_db(job_id, member_id)
    elif job.job_type == EmailServiceJobType.CERTIFICATE_CUSTOM:
        recipient = db.get_recipient_by_email(job_id, member_id_or_email)
        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recipient with email '{member_id_or_email}' not found in job {job_id}",
            )
        certificate = db.get_certificate_for_recipient(recipient.id)
        if not certificate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certificate for '{member_id_or_email}' not found",
            )
        file_path = Path(settings.certificates_folder) / certificate.certificate_path
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job type for certificate download: {job.job_type}",
        )

    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate file not found",
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=file_path.name,
    )
