import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Request, HTTPException, status
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.models.schemas import (
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
    process_certificate_attendance_job,
    process_certificate_custom_job,
)
from app.services.external_api import ExternalAPIService, ExternalAPIError
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
    "/{event_id:int}",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create attendance certificate job",
    description="Send certificates to all attendees of an event (fetches attendance from external API)",
)
async def create_attendance_certificates(
    request: Request,
    event_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    credentials=Depends(admin_guard),
):
    db = DatabaseService(session)

    event = db.get_event_or_raise(event_id)

    if db.is_event_processing(event_id):
        raise JobAlreadyProcessingError(event_id, event.name)

    auth_token = _extract_auth_header(request)
    external_api = ExternalAPIService(auth_token)
    
    try:
        attendance_data = external_api.get_attendance(event_id)
    except ExternalAPIError as e:
        logger.error(f"Failed to fetch attendance: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": f"Failed to fetch attendance data: {e.message}",
                "details": e.details,
            },
        )

    attendance_list = attendance_data.get("attendance", [])
    member_ids = []
    
    for item in attendance_list:
        member = item.get("Members", {})
        member_id = member.get("id")
        if member_id:
            member_ids.append(member_id)

    if not member_ids:
        from app.db.schema import EmailServiceJobStatus
        job = db.create_certificate_attendance_job(
            event_id=event_id,
            member_ids=[],
        )
        db.update_job_status(job.id, status=EmailServiceJobStatus.COMPLETED)
        
        logger.info(f"No attendees found for event {event_id}, created empty job {job.id}")
        
        return JobResponse(
            job_id=job.id,
            event_id=job.event_id,
            event_name=event.name,
            job_type=JobType.certificate_attendance,
            status=JobStatus.completed,
            progress=JobProgress(total=0, completed=0, successful=0, failed=0),
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    job = db.create_certificate_attendance_job(
        event_id=event_id,
        member_ids=member_ids,
    )

    background_tasks.add_task(
        process_certificate_attendance_job,
        job_id=job.id,
    )

    logger.info(
        f"Created attendance job {job.id} for event '{event.name}' with {len(member_ids)} attendees"
    )

    return JobResponse(
        job_id=job.id,
        event_id=job.event_id,
        event_name=event.name,
        job_type=JobType.certificate_attendance,
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
    description="Create a certificate generation job with custom recipients or member IDs",
)
async def create_custom_certificates(
    request: CustomCertificateRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    credentials=Depends(admin_guard),
):
    db = DatabaseService(session)

    event_id = request.event_id
    event_name = request.event_name
    event_date = request.event_date
    official = request.official

    if event_id:
        event = db.get_event_or_raise(event_id)
        event_name = event.name
        event_date = event.start_datetime.strftime("%Y-%m-%d")
        official = bool(event.is_official)

    recipients_data = None
    member_ids = None

    if request.member_ids:
        members = db.get_members(request.member_ids)
        found_ids = {m.id for m in members}
        missing_ids = set(request.member_ids) - found_ids

        if missing_ids:
            raise MemberNotFoundError(list(missing_ids)[0])

        member_ids = request.member_ids
    else:
        recipients_data = [r.model_dump() for r in request.recipients or []]

    job = db.create_certificate_job_custom(
        recipients=recipients_data,
        member_ids=member_ids,
        event_id=event_id,
        event_name=event_name,
        event_date=event_date,
        official=official if official is not None else False,
    )

    background_tasks.add_task(
        process_certificate_custom_job,
        job_id=job.id,
    )

    recipient_count = len(member_ids) if member_ids else len(recipients_data or [])

    logger.info(
        f"Created custom job {job.id} for '{event_name}' with {recipient_count} recipients"
    )

    return JobResponse(
        job_id=job.id,
        event_id=job.event_id,
        event_name=event_name or "Unknown Event",
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

    if job.job_type == EmailServiceJobType.CERTIFICATE_ATTENDANCE:
        try:
            member_id = int(member_id_or_email)
        except ValueError:
            raise RecordNotFoundError(
                "Member",
                member_id_or_email,
                {
                    "hint": "For certificate_attendance jobs, member_id must be an integer"
                },
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


def _extract_auth_header(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None
