import logging
import tempfile

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import CertificateFormat
from app.services.certificate import (
    CertificateLanguage,
    MembersGender,
    generate_certificate,
    resolve_template,
)
from app.services.storage import upload_certificate

logger = logging.getLogger(__name__)

router = APIRouter()


class EventInfo(BaseModel):
    name: str
    date: str
    official: bool


class MemberInfo(BaseModel):
    name: str
    gender: MembersGender


class CertificateGenerationRequest(BaseModel):
    language: CertificateLanguage
    format: CertificateFormat
    event: EventInfo
    member: MemberInfo


@router.post("/certificate", status_code=status.HTTP_200_OK)
def generate_certificate_endpoint(request: CertificateGenerationRequest):
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

            url = upload_certificate(png_path, request.format.value)

        return {"url": url}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Certificate generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None
