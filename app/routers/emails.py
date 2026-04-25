import logging
import tempfile

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.config import EmailLogsFromAddress
from app.services.certificate import (
    CertificateLanguage,
    MembersGender,
    generate_certificate,
    resolve_template,
)
from app.services.email import send_certificate_email

logger = logging.getLogger(__name__)

router = APIRouter()


class EventInfo(BaseModel):
    name: str
    date: str
    official: bool


class MemberInfo(BaseModel):
    name: str
    email: EmailStr
    gender: MembersGender


class CertificateRequest(BaseModel):
    from_address: EmailLogsFromAddress
    language: CertificateLanguage
    event: EventInfo
    member: MemberInfo


@router.post("/certificate", status_code=status.HTTP_200_OK)
def send_certificate(request: CertificateRequest):
    try:
        template = resolve_template(request.language, request.event.official)
        if not template.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Template not found: {template}",
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            png_path = generate_certificate(
                svg_certificate_file_path=str(template),
                name=request.member.name,
                event_name=request.event.name,
                date=request.event.date,
                gender=request.member.gender,
                lang=request.language,
                output_dir=tmp_dir,
            )

            send_certificate_email(
                from_address=request.from_address,
                recipient=request.member.email,
                name=request.member.name,
                event_name=request.event.name,
                png_path=png_path,
            )

        return {"status": "sent", "email": request.member.email}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Certificate request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None
