import shutil
import smtplib

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter

from app.config import APP_PASSWORDS, SMTP_HOST, SMTP_PORT, EmailLogsFromAddress
from app.services.email import _ses_client

router = APIRouter()


@router.get("/health")
def health_check():
    rsvg_available = shutil.which("rsvg-convert") is not None

    # Google/SMTP is the default sending path, so overall health is gated on it.
    smtp_ok = True
    smtp_error = None
    try:
        test_addr = EmailLogsFromAddress.INFO_KERNELTICS
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(test_addr.value, APP_PASSWORDS[test_addr])
    except Exception as e:
        smtp_ok = False
        smtp_error = str(e)

    # SES is optional and admin-selected, so it's reported but doesn't gate overall health.
    ses_ok = True
    ses_error = None
    try:
        _ses_client().get_send_quota()
    except (BotoCoreError, ClientError) as e:
        ses_ok = False
        ses_error = str(e)

    overall = "healthy" if rsvg_available and smtp_ok else "degraded"
    return {
        "status": overall,
        "rsvg_convert": "available" if rsvg_available else "missing",
        "smtp": "ok" if smtp_ok else f"error: {smtp_error}",
        "ses": "ok" if ses_ok else f"error: {ses_error}",
    }
