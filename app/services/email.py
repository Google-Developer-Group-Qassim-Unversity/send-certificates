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

    sender_email = from_address.value
    app_password = APP_PASSWORDS[from_address]

    logger.info(f"Sending email from {sender_email} to {recipient}")

    last_error = "Unknown error"
    for attempt in range(MAX_RETRIES):
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
                smtp.starttls()
                smtp.login(sender_email, app_password)
                smtp.send_message(msg)
                logger.info(f"Email sent to {recipient}")
                return
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {recipient}: {last_error}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(EMAIL_DELAY)

    raise RuntimeError(f"Failed after {MAX_RETRIES} attempts: {last_error}")


def send_blast_email(
    from_address: EmailLogsFromAddress,
    recipients: list[str],
    html_content: str,
    subject: str,
    preview_text: str | None = None,
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

    sender_email = from_address.value
    app_password = APP_PASSWORDS[from_address]

    logger.info(f"Sending blast email to {len(recipients)} recipients via BCC")

    last_error = "Unknown error"
    for attempt in range(MAX_RETRIES):
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
                smtp.starttls()
                smtp.login(sender_email, app_password)
                smtp.send_message(msg)
                logger.info(f"Blast email sent to {len(recipients)} recipients")
                return
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Blast attempt {attempt + 1}/{MAX_RETRIES} failed: {last_error}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(EMAIL_DELAY)

    raise RuntimeError(f"Blast failed after {MAX_RETRIES} attempts: {last_error}")
