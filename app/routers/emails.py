import logging
import tempfile

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, model_validator

from app.config import EmailLogsFromAddress, EmailProvider
from app.services.certificate import (
    CertificateLanguage,
    MembersGender,
    generate_certificate,
    resolve_template,
)
from app.services.email import send_certificate_email, send_custom_html_email

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


class ProviderRequest(BaseModel):
    provider: EmailProvider = EmailProvider.GOOGLE
    from_address: EmailLogsFromAddress | None = None

    @model_validator(mode="after")
    def validate_provider(self) -> "ProviderRequest":
        if self.provider == EmailProvider.GOOGLE and self.from_address is None:
            raise ValueError("from_address is required when provider is 'google'")
        return self


class CertificateRequest(ProviderRequest):
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
                provider=request.provider,
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


class CustomEmailAttachment(BaseModel):
    url: str
    filename: str
    content_type: str | None = None


class CustomEmailRequest(ProviderRequest):
    recipient_email: EmailStr
    subject: str
    html_content: str
    event: EventInfo
    member: MemberInfo
    language: CertificateLanguage
    attachments: list[CustomEmailAttachment] = []


@router.post("/custom", status_code=status.HTTP_200_OK)
def send_custom_email(request: CustomEmailRequest):
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
            with open(png_path, "rb") as f:
                certificate_content = f.read()

            attachments_data: list[tuple[bytes, str, str]] = [
                (certificate_content, f"{request.event.name} شهادة حضور.png", "image/png")
            ]

            with httpx.Client(timeout=30.0) as client:
                for attachment in request.attachments:
                    response = client.get(attachment.url)
                    response.raise_for_status()
                    content_type = attachment.content_type or response.headers.get(
                        "content-type", "application/octet-stream"
                    )
                    attachments_data.append((response.content, attachment.filename, content_type))

            send_custom_html_email(
                provider=request.provider,
                from_address=request.from_address,
                recipient=request.recipient_email,
                subject=request.subject,
                html_content=request.html_content,
                attachments=attachments_data,
            )

        return {"status": "sent", "email": request.recipient_email}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Custom email request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None


class DirectEmailRequest(ProviderRequest):
    recipient_email: EmailStr
    subject: str
    html_content: str
    attachments: list[CustomEmailAttachment] = []


@router.post("/direct", status_code=status.HTTP_200_OK)
def send_direct_email(request: DirectEmailRequest):
    try:
        attachments_data: list[tuple[bytes, str, str]] = []
        with httpx.Client(timeout=30.0) as client:
            for attachment in request.attachments:
                response = client.get(attachment.url)
                response.raise_for_status()
                content_type = attachment.content_type or response.headers.get(
                    "content-type", "application/octet-stream"
                )
                attachments_data.append((response.content, attachment.filename, content_type))

        send_custom_html_email(
            provider=request.provider,
            from_address=request.from_address,
            recipient=request.recipient_email,
            subject=request.subject,
            html_content=request.html_content,
            attachments=attachments_data,
        )

        return {"status": "sent", "email": request.recipient_email}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Direct email request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None
