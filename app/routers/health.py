import shutil
import smtplib

from fastapi import APIRouter

from app.config import APP_PASSWORDS, EmailLogsFromAddress, SMTP_HOST, SMTP_PORT

router = APIRouter()


@router.get("/health")
def health_check():
    rsvg_available = shutil.which("rsvg-convert") is not None

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

    overall = "healthy" if rsvg_available and smtp_ok else "degraded"
    return {
        "status": overall,
        "rsvg_convert": "available" if rsvg_available else "missing",
        "smtp": "ok" if smtp_ok else f"error: {smtp_error}",
    }
