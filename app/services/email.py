import logging
import time
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage

import boto3
from botocore.exceptions import ClientError

from app.config import (
    AWS_REGION,
    EMAIL_TEMPLATE_PATH,
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    SEND_CONCURRENCY,
    SES_ACCESS_KEY_ID,
    SES_FROM_ADDRESS,
    SES_SECRET_ACCESS_KEY,
)

logger = logging.getLogger(__name__)

# Throttling/quota errors are worth retrying with backoff; anything else (bad
# address, message rejected) will just fail again, so don't burn retries on it.
RETRYABLE_SES_ERRORS = {"Throttling", "TooManyRequestsException", "ServiceUnavailable"}

# SES hard-caps recipients (To+Cc+Bcc) per raw message at 50, unlike Gmail's BCC
# headroom -- a blast has to be split into chunks, not sent as one giant BCC.
SES_MAX_RECIPIENTS_PER_MESSAGE = 50


def _chunk(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _ses_client():
    return boto3.client(
        "ses",
        region_name=AWS_REGION,
        aws_access_key_id=SES_ACCESS_KEY_ID,
        aws_secret_access_key=SES_SECRET_ACCESS_KEY,
    )


def _send_with_retry(msg: EmailMessage, *, log_label: str) -> None:
    client = _ses_client()
    last_error = "Unknown error"
    for attempt in range(MAX_RETRIES):
        try:
            client.send_raw_email(RawMessage={"Data": msg.as_bytes()})
            logger.info(f"{log_label} sent")
            return
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            last_error = str(e)
            logger.warning(f"{log_label} attempt {attempt + 1}/{MAX_RETRIES} failed: {last_error}")
            if code not in RETRYABLE_SES_ERRORS or attempt >= MAX_RETRIES - 1:
                raise RuntimeError(f"{log_label} failed: {last_error}") from e
            time.sleep(RETRY_BASE_DELAY * (2**attempt))

    raise RuntimeError(f"{log_label} failed after {MAX_RETRIES} attempts: {last_error}")


def send_certificate_email(
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
    msg["From"] = SES_FROM_ADDRESS
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

    logger.info(f"Sending email from {SES_FROM_ADDRESS} to {recipient}")
    _send_with_retry(msg, log_label=f"Email to {recipient}")


def _build_blast_message(
    recipients: list[str],
    html_content: str,
    subject: str,
    preview_text: str | None,
    attachments: list[tuple[bytes, str, str]] | None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = SES_FROM_ADDRESS
    msg["To"] = SES_FROM_ADDRESS
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
    return msg


def send_blast_email(
    recipients: list[str],
    html_content: str,
    subject: str,
    preview_text: str | None = None,
    attachments: list[tuple[bytes, str, str]] | None = None,
) -> None:
    if not recipients:
        logger.info("Skipping blast email: no recipients")
        return

    chunks = _chunk(recipients, SES_MAX_RECIPIENTS_PER_MESSAGE)
    logger.info(
        f"Sending blast email to {len(recipients)} recipients via BCC "
        f"({len(chunks)} chunk(s) of <= {SES_MAX_RECIPIENTS_PER_MESSAGE})"
    )

    def _send_chunk(chunk: list[str]) -> None:
        msg = _build_blast_message(chunk, html_content, subject, preview_text, attachments)
        _send_with_retry(msg, log_label=f"Blast chunk to {len(chunk)} recipients")

    if len(chunks) == 1:
        _send_chunk(chunks[0])
        return

    with ThreadPoolExecutor(max_workers=min(SEND_CONCURRENCY, len(chunks))) as pool:
        # list() forces every future to be awaited so a chunk failure raises here.
        list(pool.map(_send_chunk, chunks))


def send_custom_html_email(
    recipient: str,
    subject: str,
    html_content: str,
    attachments: list[tuple[bytes, str, str]] | None = None,
) -> None:
    msg = EmailMessage()
    msg["From"] = SES_FROM_ADDRESS
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

    logger.info(f"Sending custom email from {SES_FROM_ADDRESS} to {recipient}")
    _send_with_retry(msg, log_label=f"Custom email to {recipient}")
