import logging
import smtplib
import time
from email.message import EmailMessage

from app.config import (
    APP_PASSWORDS,
    EMAIL_DELAY,
    EMAIL_TEMPLATE_PATH,
    MAX_RETRIES,
    SMTP_HOST,
    SMTP_PORT,
    EmailLogsFromAddress,
)

logger = logging.getLogger(__name__)


def _send_with_retry(msg: EmailMessage, from_address: EmailLogsFromAddress, *, log_label: str) -> None:
    sender_email = from_address.value
    app_password = APP_PASSWORDS[from_address]

    last_error = "Unknown error"
    for attempt in range(MAX_RETRIES):
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
                smtp.starttls()
                smtp.login(sender_email, app_password)
                smtp.send_message(msg)
                logger.info(f"{log_label} sent")
                return
        except Exception as e:
            last_error = str(e)
            logger.warning(f"{log_label} attempt {attempt + 1}/{MAX_RETRIES} failed: {last_error}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(EMAIL_DELAY)

    raise RuntimeError(f"{log_label} failed after {MAX_RETRIES} attempts: {last_error}")


def send_certificate_email(
    from_address: EmailLogsFromAddress,
    recipient: str,
    name: str,
    event_name: str,
    png_path: str,
) -> None:
    subject = f"شهادة حضور {event_name}"

    body = EMAIL_TEMPLATE_PATH.read_text(encoding="utf-8")
    with open(png_path, "rb") as f:
        png_content = f.read()

    body = body.replace("[Name]", name)
    body = body.replace("[Event Name]", event_name)

    msg = EmailMessage()
    msg["From"] = from_address.value
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content("This email contains HTML. Please view it in an HTML-compatible client.")
    msg.add_alternative(body, subtype="html")
    msg.add_attachment(
        png_content,
        maintype="image",
        subtype="png",
        filename=f"{event_name} شهادة حضور.png",
    )

    logger.info(f"Sending email from {from_address.value} to {recipient}")
    _send_with_retry(msg, from_address, log_label=f"Email to {recipient}")


def send_blast_email(
    from_address: EmailLogsFromAddress,
    recipients: list[str],
    html_content: str,
    subject: str,
    preview_text: str | None = None,
    attachments: list[tuple[bytes, str, str]] | None = None,
) -> None:
    msg = EmailMessage()
    msg["From"] = from_address.value
    msg["To"] = from_address.value
    msg["Subject"] = subject
    msg["Bcc"] = ", ".join(recipients)

    if preview_text:
        msg.set_content(preview_text)
    else:
        msg.set_content("This email contains HTML. Please view it in an HTML-compatible client.")
    msg.add_alternative(html_content, subtype="html")

    for content, filename, content_type in attachments or []:
        maintype, _, subtype = (content_type or "application/octet-stream").partition("/")
        msg.add_attachment(
            content,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=filename,
        )

    logger.info(f"Sending blast email to {len(recipients)} recipients via BCC")
    _send_with_retry(msg, from_address, log_label=f"Blast email to {len(recipients)} recipients")


def send_custom_html_email(
    from_address: EmailLogsFromAddress,
    recipient: str,
    subject: str,
    html_content: str,
    attachments: list[tuple[bytes, str, str]] | None = None,
) -> None:
    msg = EmailMessage()
    msg["From"] = from_address.value
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content("This email contains HTML. Please view it in an HTML-compatible client.")
    msg.add_alternative(html_content, subtype="html")

    for content, filename, content_type in attachments or []:
        maintype, _, subtype = (content_type or "application/octet-stream").partition("/")
        msg.add_attachment(
            content,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=filename,
        )

    logger.info(f"Sending custom email from {from_address.value} to {recipient}")
    _send_with_retry(msg, from_address, log_label=f"Custom email to {recipient}")
