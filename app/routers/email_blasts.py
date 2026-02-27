import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, status, Query
from sqlmodel import Session

from app.models.schemas import (
    EmailBlastRequest,
    EmailBlastResponse,
    EmailBlastDetailResponse,
    EmailBlastListResponse,
    EmailBlastListItem,
    JobStatus,
    BlastDeliveryStatus,
)
from app.db.session import get_session
from app.db.schema import EmailServiceJobType
from app.services.database import DatabaseService
from app.services.email_blast import process_email_blast_job
from app.core.exceptions import (
    EventNotFoundError,
    MemberNotFoundError,
    JobNotFoundError,
    RecordNotFoundError,
    InvalidInputError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-blasts", tags=["email-blasts"])


def get_event_name(db: DatabaseService, event_id: Optional[int]) -> str:
    if event_id:
        event = db.get_event(event_id)
        return event.name if event else "Unknown"
    return "Custom"


@router.post(
    "",
    response_model=EmailBlastResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create email blast",
    description="Create a new email blast job - sends ONE email to many recipients",
)
async def create_email_blast(
    request: EmailBlastRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    db = DatabaseService(session)

    event_name = "Custom"
    if request.event_id:
        event = db.get_event_or_raise(request.event_id)
        event_name = event.name

    recipients_data = []
    for r in request.recipients:
        if r.member_id:
            member = db.get_member(r.member_id)
            if not member:
                raise MemberNotFoundError(r.member_id)
            if not member.email:
                raise InvalidInputError(
                    f"Member {r.member_id} has no email address",
                    details={"member_id": r.member_id},
                )
            recipients_data.append(
                {
                    "member_id": r.member_id,
                    "email": member.email,
                    "name": member.name,
                }
            )
        elif r.email:
            recipients_data.append(
                {
                    "member_id": None,
                    "email": r.email,
                    "name": r.name,
                }
            )
        else:
            raise InvalidInputError(
                "Each recipient must have either member_id or email specified",
                details={"recipient": r.model_dump()},
            )

    job, email_blast = db.create_email_blast_job(
        subject=request.subject,
        body_html=request.body_html,
        recipients=recipients_data,
        body_text=request.body_text,
        is_templated=request.is_templated,
        event_id=request.event_id,
    )

    background_tasks.add_task(
        process_email_blast_job,
        job_id=job.id,
    )

    logger.info(
        f"Created email blast job {job.id} with {len(recipients_data)} recipients"
    )

    return EmailBlastResponse(
        job_id=job.id,
        event_id=job.event_id,
        event_name=event_name,
        subject=email_blast.subject,
        is_templated=request.is_templated,
        delivery_status=BlastDeliveryStatus.pending,
        sent_count=0,
        failed_count=0,
        total_recipients=job.total,
        created_at=job.created_at,
        sent_at=None,
    )


@router.get(
    "",
    response_model=EmailBlastListResponse,
    summary="List email blasts",
    description="Get a paginated list of all email blast jobs",
)
async def list_email_blasts(
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    db = DatabaseService(session)

    jobs = db.list_jobs(
        event_id=event_id,
        job_type=EmailServiceJobType.EMAIL_BLAST,
        limit=limit,
        offset=offset,
    )

    total = db.count_jobs(
        event_id=event_id,
        job_type=EmailServiceJobType.EMAIL_BLAST,
    )

    blast_items = []
    for job in jobs:
        blast = db.get_email_blast_for_job(job.id)
        if blast:
            event_name = get_event_name(db, job.event_id)
            blast_items.append(
                EmailBlastListItem(
                    job_id=job.id,
                    event_id=job.event_id,
                    event_name=event_name,
                    subject=blast.subject,
                    delivery_status=BlastDeliveryStatus(blast.delivery_status.value),  # type: ignore
                    sent_count=blast.sent_count,
                    failed_count=blast.failed_count,
                    total_recipients=job.total,
                    created_at=job.created_at,
                )
            )

    return EmailBlastListResponse(
        total=total,
        blasts=blast_items,
    )


@router.get(
    "/{job_id}",
    response_model=EmailBlastDetailResponse,
    summary="Get email blast details",
    description="Get detailed information about an email blast job including failed recipients",
)
async def get_email_blast(
    job_id: str,
    session: Session = Depends(get_session),
):
    db = DatabaseService(session)

    job = db.get_job_or_raise(job_id)

    if job.job_type != EmailServiceJobType.EMAIL_BLAST:
        raise RecordNotFoundError(
            "EmailBlast",
            job_id,
            {"hint": f"Job {job_id} is not an email blast job (type: {job.job_type})"},
        )

    blast = db.get_email_blast_for_job_or_raise(job_id)

    event_name = get_event_name(db, job.event_id)

    return EmailBlastDetailResponse(
        job_id=job.id,
        event_id=job.event_id,
        event_name=event_name,
        subject=blast.subject,
        body_html=blast.body_html,
        body_text=blast.body_text,
        is_templated=bool(blast.is_templated),
        delivery_status=BlastDeliveryStatus(blast.delivery_status.value),  # type: ignore
        sent_count=blast.sent_count,
        failed_count=blast.failed_count,
        total_recipients=job.total,
        failed_recipients=blast.failed_recipients,
        created_at=job.created_at,
        sent_at=blast.sent_at,
    )
