import json
import logging
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import EmailStr

from app.config import EmailLogsFromAddress
from app.services.email import send_blast_email

logger = logging.getLogger(__name__)

router = APIRouter()

LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"


def _write_blast_log(
    from_address: str,
    subject: str,
    preview_text: str | None,
    emails: list[EmailStr],
    response_status: int,
    response_body: dict,
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
    from_address: Annotated[EmailLogsFromAddress, Query(description="Sender email address")],
    preview_text: Annotated[str | None, Query(description="Preview text for email clients")] = None,
):
    try:
        html_content = html.decode("utf-8")

        if not html_content.strip():
            log_path = _write_blast_log(
                from_address=from_address,
                subject=subject,
                preview_text=preview_text,
                emails=emails,
                response_status=400,
                response_body={"detail": "HTML content cannot be empty"},
            )
            logger.warning(f"Blast rejected (400): empty HTML | log={log_path.name}")

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

        response_body = {"status": "sent", "recipients": len(emails)}
        log_path = _write_blast_log(
            from_address=from_address,
            subject=subject,
            preview_text=preview_text,
            emails=emails,
            response_status=200,
            response_body=response_body,
        )
        logger.info(f"Blast sent: {len(emails)} recipients via {from_address} | log={log_path.name}")

        return {"status": "sent", "recipients": len(emails)}
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        log_path = _write_blast_log(
            from_address=from_address,
            subject=subject,
            preview_text=preview_text,
            emails=emails,
            response_status=500,
            response_body={"detail": str(e)},
            tb=tb,
        )
        logger.error(f"Blast failed (500): {e} | log={log_path.name}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None
