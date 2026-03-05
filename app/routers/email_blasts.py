import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, status, Query
from sqlmodel import Session

from app.models.schemas import (
    EmailBlastRequest,
    EmailBlastResponse,
    EmailBlastDetailResponse,
    EmailBlastListResponse,
    EmailBlastListItem,
    BlastDeliveryStatus,
)
from app.db.session import get_session
from app.db.schema import EmailServiceJobType
from app.services.database import DatabaseService
from app.services.email_blast import process_email_blast_job
from app.core.exceptions import (
    MemberNotFoundError,
    RecordNotFoundError,
    InvalidInputError,
)
from app.core.auth import admin_guard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-blasts", tags=["email-blasts"])


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
    credentials=Depends(admin_guard),
):
    db = DatabaseService(session)

    email_list = []
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
            email_list.append(member.email)
        elif r.email:
            email_list.append(r.email)
        else:
            raise InvalidInputError(
                "Each recipient must have either member_id or email specified",
                details={"recipient": r.model_dump()},
            )

    job, blast = db.create_email_blast_job(
        subject=request.subject,
        body_html=request.body_html,
        recipients=email_list,
        body_text=request.body_text,
    )

    background_tasks.add_task(
        process_email_blast_job,
        job_id=job.id,
    )

    logger.info(
        f"Created email blast job {job.id} with {len(email_list)} recipients"
    )

    return EmailBlastResponse(
        job_id=job.id,
        subject=blast.subject,
        delivery_status=BlastDeliveryStatus.pending,
        total_recipients=len(email_list),
        created_at=job.created_at,
    )


@router.get(
    "",
    response_model=EmailBlastListResponse,
    summary="List email blasts",
    description="Get a paginated list of all email blast jobs",
)
async def list_email_blasts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    credentials=Depends(admin_guard),
):
    db = DatabaseService(session)

    jobs = db.list_jobs(
        job_type=EmailServiceJobType.EMAIL_BLAST,
        limit=limit,
        offset=offset,
    )

    total = db.count_jobs(
        job_type=EmailServiceJobType.EMAIL_BLAST,
    )

    blast_items = []
    for job in jobs:
        blast = db.get_email_blast_for_job(job.id)
        if blast:
            total_recipients = len(blast.recipients) if blast.recipients else 0
            failed_count = len(blast.failed_recipients) if blast.failed_recipients else 0
            sent_count = total_recipients - failed_count
            
            blast_items.append(
                EmailBlastListItem(
                    job_id=job.id,
                    subject=blast.subject,
                    delivery_status=BlastDeliveryStatus(blast.delivery_status.value),  # type: ignore
                    sent_count=sent_count,
                    failed_count=failed_count,
                    total_recipients=total_recipients,
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
    credentials=Depends(admin_guard),
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

    total_recipients = len(blast.recipients) if blast.recipients else 0
    failed_count = len(blast.failed_recipients) if blast.failed_recipients else 0
    sent_count = total_recipients - failed_count

    return EmailBlastDetailResponse(
        job_id=job.id,
        subject=blast.subject,
        body_html=blast.body_html,
        body_text=blast.body_text,
        delivery_status=BlastDeliveryStatus(blast.delivery_status.value),  # type: ignore
        sent_count=sent_count,
        failed_count=failed_count,
        total_recipients=total_recipients,
        failed_recipients=blast.failed_recipients,
        created_at=job.created_at,
    )
