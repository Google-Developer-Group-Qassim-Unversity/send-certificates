import re
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.db.schema import (
    Events,
    Members,
    EmailServiceJob,
    EmailServiceRecipient,
    EmailServiceCertificate,
    EmailServiceJobType,
    EmailServiceJobStatus,
    EmailServiceRecipientStatus,
    EmailServiceTemplateType,
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

    def create_job(
        self,
        event_id: int,
        member_ids: list[int],
        job_type: EmailServiceJobType = EmailServiceJobType.CERTIFICATE,
    ) -> EmailServiceJob:
        job = EmailServiceJob(
            id=str(uuid.uuid4()),
            event_id=event_id,
            job_type=job_type,
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
        statement = select(EmailServiceJob)

        if event_id:
            statement = statement.where(EmailServiceJob.event_id == event_id)
        if job_type:
            statement = statement.where(EmailServiceJob.job_type == job_type)

        return len(list(self.session.exec(statement).all()))

    @staticmethod
    def sanitize_filename(name: str) -> str:
        safe = re.sub(r'[<>:"/\\|?*]', "", name)
        safe = re.sub(r"\s+", "-", safe.strip())
        return safe

    def get_certificate_storage_path(
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
