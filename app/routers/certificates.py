import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, status
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
from app.core.exceptions import (
    MemberNotFoundError,
    JobAlreadyProcessingError,
    RecordNotFoundError,
)
from app.core.auth import admin_guard

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
    credentials=Depends(admin_guard),
):
    db = DatabaseService(session)

    event = db.get_event_or_raise(request.event_id)

    if db.is_event_processing(request.event_id):
        raise JobAlreadyProcessingError(request.event_id, event.name)

    members = db.get_members(request.member_ids)
    found_ids = {m.id for m in members}
    missing_ids = set(request.member_ids) - found_ids

    assert len(found_ids) == len(members), (
        f"Duplicate members in result: expected {len(request.member_ids)}, got {len(members)} unique"
    )

    if missing_ids:
        raise MemberNotFoundError(list(missing_ids)[0])

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
    credentials=Depends(admin_guard),
):
    db = DatabaseService(session)

    if request.event_id:
        db.get_event_or_raise(request.event_id)

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
    credentials=Depends(admin_guard),
):
    db = DatabaseService(session)

    job = db.get_job_or_raise(job_id)

    file_path = None

    if job.job_type == EmailServiceJobType.CERTIFICATE_EVENT:
        try:
            member_id = int(member_id_or_email)
        except ValueError:
            raise RecordNotFoundError(
                "Member",
                member_id_or_email,
                {"hint": "For certificate_event jobs, member_id must be an integer"},
            )
        file_path = db.get_certificate_path_from_db(job_id, member_id)
        if file_path is None:
            raise RecordNotFoundError("Certificate", member_id_or_email)

    elif job.job_type == EmailServiceJobType.CERTIFICATE_CUSTOM:
        recipient = db.get_recipient_by_email(job_id, member_id_or_email)
        if not recipient:
            raise RecordNotFoundError("Recipient", member_id_or_email)
        assert recipient.id, "Recipient ID should exist"
        certificate = db.get_certificate_for_recipient(recipient.id)
        if not certificate:
            raise RecordNotFoundError("Certificate", member_id_or_email)
        file_path = Path(settings.certificates_folder) / certificate.certificate_path
    else:
        raise RecordNotFoundError(
            "Job",
            job_id,
            {"hint": f"Invalid job type for certificate download: {job.job_type}"},
        )

    if not file_path or not file_path.exists():
        raise RecordNotFoundError("CertificateFile", str(file_path))

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=file_path.name,
    )
