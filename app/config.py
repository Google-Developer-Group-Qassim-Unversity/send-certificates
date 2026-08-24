import enum
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(".env.local")


class EmailLogsFromAddress(enum.StrEnum):
    INFO_KERNELTICS = "info@kerneltics.com"
    GDG_QASSIM = "gdg.qu1@gmail.com"


class EmailProvider(enum.StrEnum):
    GOOGLE = "google"
    SES = "ses"


class CertificateFormat(enum.StrEnum):
    PNG = "png"
    PDF = "pdf"


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_DELAY = 4  # seconds between retry attempts on the Gmail SMTP path

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.5  # seconds; doubles each attempt (exponential backoff on SES throttling)
SEND_CONCURRENCY = 10  # bounded concurrency for per-recipient sends (no queue needed at this volume)

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
FONTCONFIG_FILE = ASSETS_DIR / "fonts.conf"
EMAIL_TEMPLATE_PATH = ASSETS_DIR / "email_template.html"

APP_PASSWORDS: dict[EmailLogsFromAddress, str] = {
    EmailLogsFromAddress.INFO_KERNELTICS: os.getenv("APP_PASSWORD_KERNELTICS", ""),
    EmailLogsFromAddress.GDG_QASSIM: os.getenv("APP_PASSWORD_GDG_QASSIM", ""),
}

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SES_FROM_ADDRESS = os.getenv("SES_FROM_ADDRESS", "")
# Named SES_* (not AWS_*) so it can't be confused with the R2_* creds below, and so
# it's never accidentally picked up by boto3's ambient AWS_ACCESS_KEY_ID/SECRET env-var
# discovery -- kept explicit and scoped, same pattern as the R2 client in storage.py.
SES_ACCESS_KEY_ID = os.getenv("SES_ACCESS_KEY_ID", "")
SES_SECRET_ACCESS_KEY = os.getenv("SES_SECRET_ACCESS_KEY", "")

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")

missing_app_passwords = [addr.value for addr, password in APP_PASSWORDS.items() if not password]
if missing_app_passwords:
    raise ValueError(f"Missing app passwords for: {', '.join(missing_app_passwords)}")

missing = [
    name
    for name, value in {
        "SES_FROM_ADDRESS": SES_FROM_ADDRESS,
        "SES_ACCESS_KEY_ID": SES_ACCESS_KEY_ID,
        "SES_SECRET_ACCESS_KEY": SES_SECRET_ACCESS_KEY,
    }.items()
    if not value
]
if missing:
    raise ValueError(f"Missing required env var(s): {', '.join(missing)}")
