import json
import logging
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

from app.config import EmailLogsFromAddress, EmailProvider
from app.services.email import send_blast_email

logger = logging.getLogger(__name__)

router = APIRouter()

LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"


class BlastAttachment(BaseModel):
    url: str
    filename: str
    content_type: str | None = None


def _write_blast_log(
    from_address: str,
    subject: str,
    preview_text: str | None,
    emails: list[EmailStr],
    response_status: int,
    response_body: dict,
    attachment_filenames: list[str] | None = None,
    tb: str | None = None,
) -> Path:
    LOGS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    log_path = LOGS_DIR / f"blast_{ts}.log"

    request_data = {
        "from": from_address,
        "subject": subject,
        "preview_text": preview_text,
        "emails": [str(e) for e in emails],
        "attachments": attachment_filenames or [],
    }

    lines = [
        "=== BLAST REQUEST ===",
        json.dumps(request_data, indent=4, ensure_ascii=False),
        "",
        "=== RESPONSE ===",
        f"Status: {response_status}",
        json.dumps(response_body, indent=4, ensure_ascii=False),
    ]
    if tb:
        lines.append("")
        lines.append("=== TRACEBACK ===")
        lines.append(tb)

    log_path.write_text("\n".join(lines), encoding="utf-8")
    return log_path


@router.post("", status_code=status.HTTP_200_OK)
def send_blast(
    html: Annotated[bytes, Body(media_type="text/html", description="HTML email body")],
    emails: Annotated[list[EmailStr], Query(description="Recipient email addresses")],
    subject: Annotated[str, Query(description="Email subject")],
    provider: Annotated[EmailProvider, Query(description="Sending provider")] = EmailProvider.GOOGLE,
    from_address: Annotated[
        EmailLogsFromAddress | None, Query(description="Sender email address (required when provider=google)")
    ] = None,
    preview_text: Annotated[str | None, Query(description="Preview text for email clients")] = None,
    attachments: Annotated[
        str | None, Query(description="JSON-encoded list of {url, filename, content_type} attachments")
    ] = None,
):
    if provider == EmailProvider.GOOGLE and from_address is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_address is required when provider is 'google'",
        )

    attachment_specs = [BlastAttachment.model_validate(a) for a in json.loads(attachments)] if attachments else []
    attachment_filenames = [a.filename for a in attachment_specs]
    sender_label = from_address.value if from_address else provider.value

    try:
        html_content = html.decode("utf-8")

        if not html_content.strip():
            log_path = _write_blast_log(
                from_address=sender_label,
                subject=subject,
                preview_text=preview_text,
                emails=emails,
                response_status=400,
                response_body={"detail": "HTML content cannot be empty"},
                attachment_filenames=attachment_filenames,
            )
            logger.warning(f"Blast rejected (400): empty HTML | log={log_path.name}")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HTML content cannot be empty",
            )

        attachments_data: list[tuple[bytes, str, str]] = []
        with httpx.Client(timeout=30.0) as client:
            for attachment in attachment_specs:
                response = client.get(attachment.url)
                response.raise_for_status()
                content_type = attachment.content_type or response.headers.get(
                    "content-type", "application/octet-stream"
                )
                attachments_data.append((response.content, attachment.filename, content_type))

        send_blast_email(
            provider=provider,
            from_address=from_address,
            recipients=[e for e in emails],
            html_content=html_content,
            subject=subject,
            preview_text=preview_text,
            attachments=attachments_data,
        )

        response_body = {"status": "sent", "recipients": len(emails)}
        log_path = _write_blast_log(
            from_address=sender_label,
            subject=subject,
            preview_text=preview_text,
            emails=emails,
            response_status=200,
            response_body=response_body,
            attachment_filenames=attachment_filenames,
        )
        logger.info(f"Blast sent: {len(emails)} recipients via {sender_label} | log={log_path.name}")

        return {"status": "sent", "recipients": len(emails)}
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        log_path = _write_blast_log(
            from_address=sender_label,
            subject=subject,
            preview_text=preview_text,
            emails=emails,
            response_status=500,
            response_body={"detail": str(e)},
            attachment_filenames=attachment_filenames,
            tb=tb,
        )
        logger.error(f"Blast failed (500): {e} | log={log_path.name}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None
