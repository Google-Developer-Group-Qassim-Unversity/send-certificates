import uuid
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse

from config import settings
from models import (
    CertificateRequest,
    CertificateResponse,
    JobStatusResponse,
    JobProgress,
    JobSummary,
    EventsList,
    HealthCheck,
    JobStatus,
    Member,
    Gender,
)
from storage import storage
from services import process_certificates_job, certificate_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Certificate API starting up...")
    logger.info(f"Jobs folder: {settings.jobs_folder}")
    logger.info(f"Official template: {settings.official_template}")
    logger.info(f"Unofficial template: {settings.unofficial_template}")
    yield
    # Shutdown
    logger.info("Certificate API shutting down...")


app = FastAPI(
    title="Certificate Generator API",
    description="Generate and send certificates via email",
    version="1.0.0",
    lifespan=lifespan,
)


# ============ Test Recipients ============

TEST_RECIPIENTS = [
    Member(name="Test User", email="gdg.qu1@gmail.com", gender=Gender.male),
    Member(name="مرت على بالي", email="albrrak337@gmail.com", gender=Gender.male),
    Member(
        name="عبدالاله عبدالعزيز منصور البراك",
        email="albrrak773@gmail.com",
        gender=Gender.male,
    ),
]


# ============ Endpoints ============


@app.post(
    "/certificates",
    response_model=CertificateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create certificate job",
    description="Create a new certificate generation job for multiple members",
)
async def create_certificates(
    request: CertificateRequest,
    background_tasks: BackgroundTasks,
):
    """Create a certificate generation job."""
    # Check if event is already being processed
    if storage.is_event_processing(request.event_name):
        active_job_id = storage.get_active_job_id(request.event_name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job with event name '{request.event_name}' is already being processed (job_id: {active_job_id}). Please wait until it completes.",
        )

    # Generate job ID and create folder
    job_id = str(uuid.uuid4())
    folder_name = storage.create_job_folder(request.event_name, job_id)

    # Mark event as processing
    storage.mark_event_processing(request.event_name, job_id)

    # Initialize job status
    storage.initialize_job_status(
        job_id=job_id,
        event_name=request.event_name,
        folder_name=folder_name,
        total_members=len(request.members),
    )

    # Add background task
    background_tasks.add_task(
        process_certificates_job,
        job_id=job_id,
        event_name=request.event_name,
        announced_name=request.announced_name,
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


@app.post(
    "/certificates/test",
    response_model=CertificateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create test certificate job",
    description="Create a test certificate job with hardcoded test recipients added to the members list",
)
async def create_test_certificates(
    request: CertificateRequest,
    background_tasks: BackgroundTasks,
):
    """Create a test certificate generation job with test recipients."""
    # Add test recipients to the beginning of members list
    all_members = TEST_RECIPIENTS.copy()

    # Insert one test recipient in the middle
    mid_index = len(request.members) // 2 if request.members else 0

    # Build final member list: test at start, original in middle, test at end
    final_members = [TEST_RECIPIENTS[0]]  # First test recipient
    final_members.extend(request.members[:mid_index])
    if len(TEST_RECIPIENTS) > 1:
        final_members.append(TEST_RECIPIENTS[1])  # Middle test recipient
    final_members.extend(request.members[mid_index:])
    if len(TEST_RECIPIENTS) > 2:
        final_members.append(TEST_RECIPIENTS[2])  # Last test recipient

    # Create modified request
    test_event_name = f"[TEST] {request.event_name}"

    # Check if event is already being processed
    if storage.is_event_processing(test_event_name):
        active_job_id = storage.get_active_job_id(test_event_name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Test job for event '{request.event_name}' is already being processed (job_id: {active_job_id}). Please wait until it completes.",
        )

    # Generate job ID and create folder
    job_id = str(uuid.uuid4())
    folder_name = storage.create_job_folder(test_event_name, job_id)

    # Mark event as processing
    storage.mark_event_processing(test_event_name, job_id)

    # Initialize job status
    storage.initialize_job_status(
        job_id=job_id,
        event_name=test_event_name,
        folder_name=folder_name,
        total_members=len(final_members),
    )

    # Add background task
    background_tasks.add_task(
        process_certificates_job,
        job_id=job_id,
        event_name=request.event_name,  # Use original event name in certificate
        announced_name=request.announced_name,
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


@app.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Get the current status of a certificate generation job",
)
async def get_job_status(job_id: str):
    """Get the status of a certificate job."""
    job_status = storage.get_job_status(job_id)

    if not job_status:
        # Try to find from saved summaries
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


@app.get(
    "/summary/{folder_name}",
    response_model=JobSummary,
    summary="Get job summary",
    description="Get the complete summary of a finished job including all member results",
)
async def get_job_summary(folder_name: str):
    """Get the complete summary of a job."""
    summary = storage.read_summary(folder_name)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary for folder '{folder_name}' not found",
        )

    return summary


@app.get(
    "/summaries",
    response_model=EventsList,
    summary="List all summaries",
    description="Get a list of all job summaries",
)
async def list_summaries():
    """List all job summaries."""
    events = storage.list_all_summaries()

    return EventsList(
        total=len(events),
        events=events,
    )


@app.get(
    "/certificates/{folder_name}/{filename}",
    summary="Download certificate",
    description="Download a generated PDF certificate",
)
async def download_certificate(folder_name: str, filename: str):
    """Download a certificate PDF file."""
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


@app.get(
    "/health",
    response_model=HealthCheck,
    summary="Health check",
    description="Check the health of the API and its dependencies",
)
async def health_check():
    """Check API health and dependencies."""
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
