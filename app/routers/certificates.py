import uuid
import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse

from app.models.schemas import (
    CertificateRequest,
    CertificateResponse,
    JobStatus,
    Member,
    Gender,
)
from app.services.storage import storage
from app.services.certificate import process_certificates_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/certificates", tags=["certificates"])

TEST_RECIPIENTS = [
    Member(name="Test User", email="gdg.qu1@gmail.com", gender=Gender.male),
    Member(name="مرت على بالي", email="albrrak337@gmail.com", gender=Gender.male),
    Member(
        name="عبدالاله عبدالعزيز منصور البراك",
        email="albrrak773@gmail.com",
        gender=Gender.male,
    ),
]


@router.post(
    "",
    response_model=CertificateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create certificate job",
    description="Create a new certificate generation job for multiple members",
)
async def create_certificates(
    request: CertificateRequest,
    background_tasks: BackgroundTasks,
):
    if storage.is_event_processing(request.event_name):
        active_job_id = storage.get_active_job_id(request.event_name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job with event name '{request.event_name}' is already being processed (job_id: {active_job_id}). Please wait until it completes.",
        )

    job_id = str(uuid.uuid4())
    folder_name = storage.create_job_folder(request.event_name, job_id)

    storage.mark_event_processing(request.event_name, job_id)

    storage.initialize_job_status(
        job_id=job_id,
        event_name=request.event_name,
        folder_name=folder_name,
        total_members=len(request.members),
    )

    background_tasks.add_task(
        process_certificates_job,
        job_id=job_id,
        event_name=request.event_name,
        date=request.date,
        official=request.official,
        members=request.members,
        folder_name=folder_name,
    )

    logger.info(
        f"Created job {job_id} for event '{request.event_name}' with {len(request.members)} members"
    )

    return CertificateResponse(
        job_id=job_id,
        event_name=request.event_name,
        folder_name=folder_name,
        status=JobStatus.pending,
        message=f"Job created and queued for processing. {len(request.members)} certificates will be generated.",
    )


@router.post(
    "/test",
    response_model=CertificateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create test certificate job",
    description="Create a test certificate job with hardcoded test recipients added to the members list",
)
async def create_test_certificates(
    request: CertificateRequest,
    background_tasks: BackgroundTasks,
):
    mid_index = len(request.members) // 2 if request.members else 0

    final_members = [TEST_RECIPIENTS[0]]
    final_members.extend(request.members[:mid_index])
    if len(TEST_RECIPIENTS) > 1:
        final_members.append(TEST_RECIPIENTS[1])
    final_members.extend(request.members[mid_index:])
    if len(TEST_RECIPIENTS) > 2:
        final_members.append(TEST_RECIPIENTS[2])

    test_event_name = f"[TEST] {request.event_name}"

    if storage.is_event_processing(test_event_name):
        active_job_id = storage.get_active_job_id(test_event_name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Test job for event '{request.event_name}' is already being processed (job_id: {active_job_id}). Please wait until it completes.",
        )

    job_id = str(uuid.uuid4())
    folder_name = storage.create_job_folder(test_event_name, job_id)

    storage.mark_event_processing(test_event_name, job_id)

    storage.initialize_job_status(
        job_id=job_id,
        event_name=test_event_name,
        folder_name=folder_name,
        total_members=len(final_members),
    )

    background_tasks.add_task(
        process_certificates_job,
        job_id=job_id,
        event_name=request.event_name,
        date=request.date,
        official=request.official,
        members=final_members,
        folder_name=folder_name,
    )

    logger.info(
        f"Created TEST job {job_id} for event '{request.event_name}' with {len(final_members)} members (including {len(TEST_RECIPIENTS)} test recipients)"
    )

    return CertificateResponse(
        job_id=job_id,
        event_name=test_event_name,
        folder_name=folder_name,
        status=JobStatus.pending,
        message=f"Test job created. {len(final_members)} certificates will be generated (including {len(TEST_RECIPIENTS)} test recipients).",
    )


@router.get(
    "/{folder_name}/{filename}",
    summary="Download certificate",
    description="Download a generated PDF certificate",
)
async def download_certificate(folder_name: str, filename: str):
    file_path = storage.get_certificate_path(folder_name, filename)

    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate file '{filename}' not found in folder '{folder_name}'",
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename,
    )
