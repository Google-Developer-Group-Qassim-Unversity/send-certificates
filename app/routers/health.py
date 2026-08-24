import shutil

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter

from app.services.email import _ses_client

router = APIRouter()


@router.get("/health")
def health_check():
    rsvg_available = shutil.which("rsvg-convert") is not None

    ses_ok = True
    ses_error = None
    try:
        _ses_client().get_send_quota()
    except (BotoCoreError, ClientError) as e:
        ses_ok = False
        ses_error = str(e)

    overall = "healthy" if rsvg_available and ses_ok else "degraded"
    return {
        "status": overall,
        "rsvg_convert": "available" if rsvg_available else "missing",
        "ses": "ok" if ses_ok else f"error: {ses_error}",
    }
