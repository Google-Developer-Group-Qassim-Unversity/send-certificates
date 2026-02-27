import re
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

from sqlmodel import Session, select, func

from app.db.schema import (
    Events,
    Members,
    EmailServiceJob,
    EmailServiceRecipient,
    EmailServiceCertificate,
    EmailServiceEmailBlast,
    EmailServiceJobType,
    EmailServiceJobStatus,
    EmailServiceRecipientStatus,
    EmailServiceTemplateType,
    EmailBlastDeliveryStatus,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self, session: Session):
        self.session = session

    def get_event(self, event_id: int) -> Optional[Events]:
        return self.session.get(Events, event_id)

    def get_member(self, member_id: int) -> Optional[Members]:
        return self.session.get(Members, member_id)

    def get_members(self, member_ids: list[int]) -> list[Members]:
        statement = select(Members).where(Members.id.in_(member_ids))
        return list(self.session.exec(statement).all())

    def is_event_processing(self, event_id: int) -> bool:
        statement = (
            select(EmailServiceJob)
            .where(EmailServiceJob.event_id == event_id)
            .where(
                EmailServiceJob.status.in_(
                    [
                        EmailServiceJobStatus.PENDING,
                        EmailServiceJobStatus.PROCESSING,
                    ]
                )
            )
        )
        return self.session.exec(statement).first() is not None

    def get_active_job_for_event(self, event_id: int) -> Optional[EmailServiceJob]:
        statement = (
            select(EmailServiceJob)
            .where(EmailServiceJob.event_id == event_id)
            .where(
                EmailServiceJob.status.in_(
                    [
                        EmailServiceJobStatus.PENDING,
                        EmailServiceJobStatus.PROCESSING,
                    ]
                )
            )
        )
        return self.session.exec(statement).first()

    def create_certificate_job_for_event(
        self,
        event_id: int,
        member_ids: list[int],
    ) -> EmailServiceJob:
        job = EmailServiceJob(
            id=str(uuid.uuid4()),
            event_id=event_id,
            job_type=EmailServiceJobType.CERTIFICATE_EVENT,
            status=EmailServiceJobStatus.PENDING,
            total=len(member_ids),
            completed=0,
            successful=0,
            failed=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(job)

        for member_id in member_ids:
            recipient = EmailServiceRecipient(
                job_id=job.id,
                member_id=member_id,
                status=EmailServiceRecipientStatus.PENDING,
            )
            self.session.add(recipient)

        self.session.commit()
        self.session.refresh(job)
        return job

    def create_certificate_job_custom(
        self,
        recipients: list[dict],
        event_name: str,
        event_date: str,
        official: bool,
        event_id: Optional[int] = None,
    ) -> EmailServiceJob:
        job_config = {
            "event_name": event_name,
            "event_date": event_date,
            "official": official,
        }

        job = EmailServiceJob(
            id=str(uuid.uuid4()),
            event_id=event_id,
            job_type=EmailServiceJobType.CERTIFICATE_CUSTOM,
            job_config=job_config,
            status=EmailServiceJobStatus.PENDING,
            total=len(recipients),
            completed=0,
            successful=0,
            failed=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(job)

        for r in recipients:
            recipient = EmailServiceRecipient(
                job_id=job.id,
                email=r.get("email"),
                name=r.get("name"),
                custom_data=r.get("custom_data"),
                status=EmailServiceRecipientStatus.PENDING,
            )
            self.session.add(recipient)

        self.session.commit()
        self.session.refresh(job)
        return job

    def create_email_blast_job(
        self,
        subject: str,
        body_html: str,
        recipients: list[dict],
        body_text: Optional[str] = None,
        is_templated: bool = False,
        event_id: Optional[int] = None,
    ) -> tuple[EmailServiceJob, EmailServiceEmailBlast]:
        job_config = {
            "is_templated": is_templated,
            "recipients": recipients,
        }

        job = EmailServiceJob(
            id=str(uuid.uuid4()),
            event_id=event_id,
            job_type=EmailServiceJobType.EMAIL_BLAST,
            job_config=job_config,
            status=EmailServiceJobStatus.PENDING,
            total=len(recipients),
            completed=0,
            successful=0,
            failed=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(job)
        self.session.flush()

        email_blast = EmailServiceEmailBlast(
            job_id=job.id,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            is_templated=1 if is_templated else 0,
            delivery_status=EmailBlastDeliveryStatus.PENDING,
            sent_count=0,
            failed_count=0,
            failed_recipients=[],
        )
        self.session.add(email_blast)

        self.session.commit()
        self.session.refresh(job)
        self.session.refresh(email_blast)
        return job, email_blast

    def get_job(self, job_id: str) -> Optional[EmailServiceJob]:
        return self.session.get(EmailServiceJob, job_id)

    def update_job_status(
        self,
        job_id: str,
        status: Optional[EmailServiceJobStatus] = None,
        increment_completed: bool = False,
        increment_successful: bool = False,
        increment_failed: bool = False,
    ) -> None:
        job = self.session.get(EmailServiceJob, job_id)
        if not job:
            return

        if status:
            job.status = status
        if increment_completed:
            job.completed += 1
        if increment_successful:
            job.successful += 1
        if increment_failed:
            job.failed += 1
        job.updated_at = datetime.utcnow()

        if (
            status == EmailServiceJobStatus.COMPLETED
            or status == EmailServiceJobStatus.FAILED
        ):
            job.completed_at = datetime.utcnow()

        self.session.add(job)
        self.session.commit()

    def get_recipient(self, recipient_id: int) -> Optional[EmailServiceRecipient]:
        return self.session.get(EmailServiceRecipient, recipient_id)

    def get_recipients_for_job(self, job_id: str) -> list[EmailServiceRecipient]:
        statement = (
            select(EmailServiceRecipient)
            .where(EmailServiceRecipient.job_id == job_id)
            .order_by(EmailServiceRecipient.id)
        )
        return list(self.session.exec(statement).all())

    def update_recipient_status(
        self,
        recipient_id: int,
        status: EmailServiceRecipientStatus,
        error: Optional[str] = None,
    ) -> None:
        recipient = self.session.get(EmailServiceRecipient, recipient_id)
        if not recipient:
            return

        recipient.status = status
        if status == EmailServiceRecipientStatus.SENT:
            recipient.sent_at = datetime.utcnow()
        if error:
            recipient.error = error

        self.session.add(recipient)
        self.session.commit()

    def create_certificate(
        self,
        recipient_id: int,
        certificate_path: str,
        template_type: EmailServiceTemplateType,
    ) -> EmailServiceCertificate:
        certificate = EmailServiceCertificate(
            recipient_id=recipient_id,
            certificate_path=certificate_path,
            template_type=template_type,
        )
        self.session.add(certificate)
        self.session.commit()
        self.session.refresh(certificate)
        return certificate

    def get_certificate_for_recipient(
        self, recipient_id: int
    ) -> Optional[EmailServiceCertificate]:
        statement = select(EmailServiceCertificate).where(
            EmailServiceCertificate.recipient_id == recipient_id
        )
        return self.session.exec(statement).first()

    def get_email_blast_for_job(self, job_id: str) -> Optional[EmailServiceEmailBlast]:
        statement = select(EmailServiceEmailBlast).where(
            EmailServiceEmailBlast.job_id == job_id
        )
        return self.session.exec(statement).first()

    def update_email_blast(
        self,
        blast_id: int,
        delivery_status: Optional[EmailBlastDeliveryStatus] = None,
        sent_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        failed_recipients: Optional[list] = None,
        provider_response: Optional[dict] = None,
    ) -> EmailServiceEmailBlast:
        blast = self.session.get(EmailServiceEmailBlast, blast_id)
        if not blast:
            raise ValueError(f"Email blast {blast_id} not found")

        if delivery_status:
            blast.delivery_status = delivery_status
        if sent_count is not None:
            blast.sent_count = sent_count
        if failed_count is not None:
            blast.failed_count = failed_count
        if failed_recipients is not None:
            blast.failed_recipients = failed_recipients
        if provider_response is not None:
            blast.provider_response = provider_response

        if delivery_status in [
            EmailBlastDeliveryStatus.SENT,
            EmailBlastDeliveryStatus.PARTIAL,
        ]:
            blast.sent_at = datetime.utcnow()

        self.session.add(blast)
        self.session.commit()
        self.session.refresh(blast)
        return blast

    def list_jobs(
        self,
        event_id: Optional[int] = None,
        job_type: Optional[EmailServiceJobType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EmailServiceJob]:
        statement = select(EmailServiceJob).order_by(EmailServiceJob.created_at.desc())

        if event_id:
            statement = statement.where(EmailServiceJob.event_id == event_id)
        if job_type:
            statement = statement.where(EmailServiceJob.job_type == job_type)

        statement = statement.offset(offset).limit(limit)
        return list(self.session.exec(statement).all())

    def count_jobs(
        self,
        event_id: Optional[int] = None,
        job_type: Optional[EmailServiceJobType] = None,
    ) -> int:
        statement = select(func.count()).select_from(EmailServiceJob)

        if event_id:
            statement = statement.where(EmailServiceJob.event_id == event_id)
        if job_type:
            statement = statement.where(EmailServiceJob.job_type == job_type)

        return self.session.exec(statement).one()

    @staticmethod
    def sanitize_filename(name: str) -> str:
        safe = re.sub(r'[<>:"/\\|?*]', "", name)
        safe = re.sub(r"\s+", "-", safe.strip())
        return safe

    def get_certificate_storage_path_for_event(
        self,
        event_id: int,
        event_name: str,
        member_id: int,
        member_name: str,
    ) -> Path:
        base_path = Path(settings.certificates_folder)

        safe_event_name = self.sanitize_filename(event_name)
        event_folder = f"{event_id}-{safe_event_name}"

        safe_member_name = self.sanitize_filename(member_name)
        filename = f"{member_id}-{safe_member_name}.pdf"

        full_path = base_path / event_folder / filename
        full_path.parent.mkdir(parents=True, exist_ok=True)

        return full_path

    def get_certificate_storage_path_custom(
        self,
        job_id: str,
        event_name: str,
        recipient_email: str,
        recipient_name: str,
    ) -> Path:
        base_path = Path(settings.certificates_folder)

        safe_event_name = self.sanitize_filename(event_name)
        event_folder = f"custom-{job_id[:8]}-{safe_event_name}"

        safe_recipient_name = self.sanitize_filename(recipient_name)
        safe_email = self.sanitize_filename(recipient_email)
        filename = f"{safe_email}-{safe_recipient_name}.pdf"

        full_path = base_path / event_folder / filename
        full_path.parent.mkdir(parents=True, exist_ok=True)

        return full_path

    def get_certificate_path_from_db(
        self, job_id: str, member_id: int
    ) -> Optional[Path]:
        statement = (
            select(EmailServiceRecipient)
            .where(EmailServiceRecipient.job_id == job_id)
            .where(EmailServiceRecipient.member_id == member_id)
        )
        recipient = self.session.exec(statement).first()

        if not recipient:
            return None

        certificate = self.get_certificate_for_recipient(recipient.id)
        if not certificate:
            return None

        file_path = Path(settings.certificates_folder) / certificate.certificate_path
        if file_path.exists():
            return file_path
        return None

    def get_recipient_by_email(
        self, job_id: str, email: str
    ) -> Optional[EmailServiceRecipient]:
        statement = (
            select(EmailServiceRecipient)
            .where(EmailServiceRecipient.job_id == job_id)
            .where(EmailServiceRecipient.email == email)
        )
        return self.session.exec(statement).first()
