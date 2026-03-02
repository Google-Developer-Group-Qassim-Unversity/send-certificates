import re
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

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
from app.core.exceptions import (
    RecordNotFoundError,
    TransactionError,
    EventNotFoundError,
    JobNotFoundError,
)

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self, session: Session):
        self.session = session

    def get_event(self, event_id: int) -> Optional[Events]:
        return self.session.get(Events, event_id)

    def get_event_or_raise(self, event_id: int) -> Events:
        event = self.get_event(event_id)
        if not event:
            raise EventNotFoundError(event_id)
        return event

    def get_member(self, member_id: int) -> Optional[Members]:
        return self.session.get(Members, member_id)

    def get_members(self, member_ids: list[int]) -> list[Members]:
        statement = select(Members).where(Members.id.in_(member_ids))  # type: ignore[union-attr]
        return list(self.session.exec(statement).all())

    def is_event_processing(self, event_id: int) -> bool:
        statement = (
            select(EmailServiceJob)
            .where(EmailServiceJob.event_id == event_id)
            .where(
                EmailServiceJob.status.in_(  # type: ignore[union-attr]
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
                EmailServiceJob.status.in_(  # type: ignore[union-attr]
                    [
                        EmailServiceJobStatus.PENDING,
                        EmailServiceJobStatus.PROCESSING,
                    ]
                )
            )
        )
        return self.session.exec(statement).first()

    def create_certificate_attendance_job(
        self,
        event_id: int,
        member_ids: list[int],
    ) -> EmailServiceJob:
        try:
            job = EmailServiceJob(
                id=str(uuid.uuid4()),
                event_id=event_id,
                job_type=EmailServiceJobType.CERTIFICATE_ATTENDANCE,
                status=EmailServiceJobStatus.PENDING,
                total=len(member_ids),
                completed=0,
                successful=0,
                failed=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
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

            assert job.id, "Job ID should be set after commit"
            return job
        except Exception as e:
            self.session.rollback()
            raise TransactionError(
                f"Failed to create certificate attendance job for event {event_id}",
                details={
                    "event_id": event_id,
                    "member_count": len(member_ids),
                    "error": str(e),
                },
            ) from e

    def create_certificate_job_custom(
        self,
        event_name: Optional[str],
        event_date: Optional[str],
        official: bool,
        event_id: Optional[int] = None,
        recipients: Optional[list[dict]] = None,
        member_ids: Optional[list[int]] = None,
    ) -> EmailServiceJob:
        job_config = {
            "event_name": event_name or "Custom Event",
            "event_date": event_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "official": official,
        }

        total_count = (
            len(member_ids) if member_ids else len(recipients) if recipients else 0
        )

        try:
            job = EmailServiceJob(
                id=str(uuid.uuid4()),
                event_id=event_id,
                job_type=EmailServiceJobType.CERTIFICATE_CUSTOM,
                job_config=job_config,
                status=EmailServiceJobStatus.PENDING,
                total=total_count,
                completed=0,
                successful=0,
                failed=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.session.add(job)

            if member_ids:
                for member_id in member_ids:
                    recipient = EmailServiceRecipient(
                        job_id=job.id,
                        member_id=member_id,
                        status=EmailServiceRecipientStatus.PENDING,
                    )
                    self.session.add(recipient)
            elif recipients:
                for r in recipients:
                    recipient = EmailServiceRecipient(
                        job_id=job.id,
                        email=r.get("email"),
                        name=r.get("name"),
                        gender=r.get("gender"),
                        status=EmailServiceRecipientStatus.PENDING,
                    )
                    self.session.add(recipient)

            self.session.commit()
            self.session.refresh(job)

            assert job.id, "Job ID should be set after commit"
            return job
        except Exception as e:
            self.session.rollback()
            raise TransactionError(
                "Failed to create custom certificate job",
                details={
                    "event_name": event_name,
                    "recipient_count": total_count,
                    "error": str(e),
                },
            ) from e

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

        try:
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
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
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

            assert job.id, "Job ID should be set after commit"
            assert email_blast.id, "Email blast ID should be set after commit"
            return job, email_blast
        except Exception as e:
            self.session.rollback()
            raise TransactionError(
                "Failed to create email blast job",
                details={
                    "subject": subject,
                    "recipient_count": len(recipients),
                    "error": str(e),
                },
            ) from e

    def get_job(self, job_id: str) -> Optional[EmailServiceJob]:
        return self.session.get(EmailServiceJob, job_id)

    def get_job_or_raise(self, job_id: str) -> EmailServiceJob:
        job = self.get_job(job_id)
        if not job:
            raise JobNotFoundError(job_id)
        return job

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
            raise JobNotFoundError(job_id)

        try:
            if status:
                job.status = status
            if increment_completed:
                job.completed += 1
            if increment_successful:
                job.successful += 1
            if increment_failed:
                job.failed += 1
            job.updated_at = datetime.now(timezone.utc)

            if (
                status == EmailServiceJobStatus.COMPLETED
                or status == EmailServiceJobStatus.FAILED
            ):
                job.completed_at = datetime.now(timezone.utc)

            self.session.add(job)
            self.session.commit()

            assert job.completed <= job.total, (
                f"Invariant violated: completed ({job.completed}) > total ({job.total}) for job {job_id}"
            )
            assert job.successful <= job.completed, (
                f"Invariant violated: successful ({job.successful}) > completed ({job.completed}) for job {job_id}"
            )
            assert job.failed <= job.completed, (
                f"Invariant violated: failed ({job.failed}) > completed ({job.completed}) for job {job_id}"
            )
            assert job.successful + job.failed <= job.completed, (
                f"Invariant violated: successful + failed ({job.successful + job.failed}) > completed ({job.completed}) for job {job_id}"
            )

        except JobNotFoundError:
            raise
        except AssertionError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise TransactionError(
                f"Failed to update job status for {job_id}",
                details={"job_id": job_id, "error": str(e)},
            ) from e

    def get_recipient(self, recipient_id: int) -> Optional[EmailServiceRecipient]:
        return self.session.get(EmailServiceRecipient, recipient_id)

    def get_recipients_for_job(self, job_id: str) -> list[EmailServiceRecipient]:
        statement = (
            select(EmailServiceRecipient)
            .where(EmailServiceRecipient.job_id == job_id)
            .order_by(EmailServiceRecipient.id)  # type: ignore[arg-type]
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
            raise RecordNotFoundError("Recipient", recipient_id)

        try:
            recipient.status = status
            if status == EmailServiceRecipientStatus.SENT:
                recipient.sent_at = datetime.now(timezone.utc)
            if error:
                recipient.error = error

            self.session.add(recipient)
            self.session.commit()
        except RecordNotFoundError:
            raise
        except Exception as e:
            self.session.rollback()
            raise TransactionError(
                f"Failed to update recipient status for {recipient_id}",
                details={"recipient_id": recipient_id, "error": str(e)},
            ) from e

    def create_certificate(
        self,
        recipient_id: int,
        certificate_path: str,
        template_type: EmailServiceTemplateType,
    ) -> EmailServiceCertificate:
        try:
            certificate = EmailServiceCertificate(
                recipient_id=recipient_id,
                certificate_path=certificate_path,
                template_type=template_type,
            )
            self.session.add(certificate)
            self.session.commit()
            self.session.refresh(certificate)

            assert certificate.id, "Certificate ID should be set after commit"
            return certificate
        except Exception as e:
            self.session.rollback()
            raise TransactionError(
                f"Failed to create certificate for recipient {recipient_id}",
                details={
                    "recipient_id": recipient_id,
                    "certificate_path": certificate_path,
                    "error": str(e),
                },
            ) from e

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

    def get_email_blast_for_job_or_raise(self, job_id: str) -> EmailServiceEmailBlast:
        blast = self.get_email_blast_for_job(job_id)
        if not blast:
            raise RecordNotFoundError(
                "EmailBlast", job_id, {"context": "email_blast_for_job"}
            )
        return blast

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
            raise RecordNotFoundError("EmailBlast", blast_id)

        try:
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
                blast.sent_at = datetime.now(timezone.utc)

            self.session.add(blast)
            self.session.commit()
            self.session.refresh(blast)

            assert blast.id, "Blast ID should exist after commit"
            return blast
        except RecordNotFoundError:
            raise
        except Exception as e:
            self.session.rollback()
            raise TransactionError(
                f"Failed to update email blast {blast_id}",
                details={"blast_id": blast_id, "error": str(e)},
            ) from e

    def list_jobs(
        self,
        event_id: Optional[int] = None,
        job_type: Optional[EmailServiceJobType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EmailServiceJob]:
        statement = select(EmailServiceJob).order_by(EmailServiceJob.created_at.desc())  # type: ignore[union-attr]

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

        assert recipient.id, "Recipient ID should exist"
        certificate = self.get_certificate_for_recipient(recipient.id)
        if not certificate:
            return None

        file_path = Path(settings.certificates_folder) / certificate.certificate_path
        if file_path.exists():
            return file_path

        logger.warning(
            f"DB-FS inconsistency: certificate record exists but file missing at {file_path}",
            extra={"job_id": job_id, "member_id": member_id, "path": str(file_path)},
        )
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
