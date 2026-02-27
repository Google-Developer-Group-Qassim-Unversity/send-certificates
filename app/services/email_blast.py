import smtplib
import time
import logging
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings
from app.db.session import engine
from app.db.schema import (
    EmailBlastDeliveryStatus,
    EmailServiceJobStatus,
    EmailServiceJobType,
)
from app.services.database import DatabaseService
from app.core.exceptions import (
    JobNotFoundError,
)

from sqlmodel import Session

logger = logging.getLogger(__name__)


class EmailBlastService:
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.sender_email = settings.sender_email
        self.app_password = settings.app_password
        self.max_retries = settings.max_retries
        self.email_delay = settings.email_delay


def process_email_blast_job(job_id: str) -> None:
    with Session(engine) as session:
        db = DatabaseService(session)

        job = db.get_job(job_id)
        if not job:
            raise JobNotFoundError(job_id)

        assert job.job_type == EmailServiceJobType.EMAIL_BLAST, (
            f"process_email_blast_job called with wrong job type: {job.job_type}"
        )

        blast = db.get_email_blast_for_job(job_id)
        assert blast is not None, (
            f"Email blast job {job_id} missing EmailServiceEmailBlast record"
        )

        db.update_job_status(job_id, status=EmailServiceJobStatus.PROCESSING)

        job_config = job.job_config or {}
        recipients_data = job_config.get("recipients", [])

        email_list = []
        name_list = []
        for r in recipients_data:
            if r.get("member_id"):
                member = db.get_member(r["member_id"])
                if member and member.email:
                    email_list.append(member.email)
                    name_list.append(member.name or "")
            elif r.get("email"):
                email_list.append(r["email"])
                name_list.append(r.get("name", ""))

        if not email_list:
            logger.error("No valid recipients found")
            assert blast.id is not None, "Blast ID should exist"
            db.update_email_blast(
                blast.id,
                delivery_status=EmailBlastDeliveryStatus.FAILED,
            )
            db.update_job_status(job_id, status=EmailServiceJobStatus.FAILED)
            return

        subject = blast.subject
        body_html = blast.body_html
        body_text = blast.body_text

        sent_count = 0
        failed_count = 0
        failed_recipients = []
        last_error: Optional[str] = None

        try:
            msg = EmailMessage()
            msg["From"] = settings.sender_email
            msg["To"] = ", ".join(email_list)
            msg["Subject"] = subject
            msg.set_content(
                body_text or "Please view this email in an HTML-compatible client."
            )

            msg.add_alternative(body_html, subtype="html")

            logger.info(f"Sending email blast to {len(email_list)} recipients")

            for attempt in range(settings.max_retries):
                try:
                    with smtplib.SMTP(
                        settings.smtp_host, settings.smtp_port, timeout=30
                    ) as smtp:
                        smtp.starttls()
                        smtp.login(settings.sender_email, settings.app_password)
                        smtp.send_message(msg)
                        logger.info("Email blast sent successfully")
                        sent_count = len(email_list)
                        break
                except smtplib.SMTPException as e:
                    last_error = f"SMTP error: {e}"
                    logger.warning(
                        f"Failed to send blast (attempt {attempt + 1}/{settings.max_retries}): {last_error}"
                    )
                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        f"Failed to send blast (attempt {attempt + 1}/{settings.max_retries}): {last_error}"
                    )

                if attempt < settings.max_retries - 1:
                    time.sleep(settings.email_delay)

            if sent_count == 0:
                failed_count = len(email_list)
                failed_recipients = [
                    {
                        "email": email_list[i],
                        "name": name_list[i],
                        "error": last_error or "Unknown error",
                    }
                    for i in range(len(email_list))
                ]

        except Exception as e:
            logger.exception(f"Unexpected error sending email blast: {e}")
            failed_count = len(email_list)
            failed_recipients = [
                {"email": email_list[i], "name": name_list[i], "error": str(e)}
                for i in range(len(email_list))
            ]

        assert sent_count + failed_count == len(email_list), (
            f"Invariant violated: sent ({sent_count}) + failed ({failed_count}) != total ({len(email_list)})"
        )

        if sent_count > 0 and failed_count == 0:
            delivery_status = EmailBlastDeliveryStatus.SENT
        elif sent_count > 0 and failed_count > 0:
            delivery_status = EmailBlastDeliveryStatus.PARTIAL
        else:
            delivery_status = EmailBlastDeliveryStatus.FAILED

        assert blast.id is not None, "Blast ID should exist"
        blast_id = blast.id
        db.update_email_blast(
            blast_id,
            delivery_status=delivery_status,
            sent_count=sent_count,
            failed_count=failed_count,
            failed_recipients=failed_recipients if failed_recipients else None,
        )

        job_status = EmailServiceJobStatus.COMPLETED
        if delivery_status == EmailBlastDeliveryStatus.FAILED:
            job_status = EmailServiceJobStatus.FAILED

        db.update_job_status(
            job_id,
            status=job_status,
        )

        logger.info(f"Job {job_id} completed with status: {delivery_status}")


email_blast_service = EmailBlastService()
