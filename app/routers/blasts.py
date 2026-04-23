import logging
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import EmailStr

from app.config import EmailLogsFromAddress
from app.services.email import send_blast_email

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", status_code=status.HTTP_200_OK)
def send_blast(
    html: bytes = Body(..., media_type="text/html", description="HTML email body"),
    emails: list[EmailStr] = Query(..., description="Recipient email addresses"),
    subject: str = Query(..., description="Email subject"),
    preview_text: Optional[str] = Query(None, description="Preview text for email clients"),
    from_address: EmailLogsFromAddress = Query(..., description="Sender email address"),
):
    try:
        html_content = html.decode("utf-8")

        if not html_content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HTML content cannot be empty",
            )

        send_blast_email(
            from_address=from_address,
            recipients=[e for e in emails],
            html_content=html_content,
            subject=subject,
            preview_text=preview_text,
        )

        return {"status": "sent", "recipients": len(emails)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Blast request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
