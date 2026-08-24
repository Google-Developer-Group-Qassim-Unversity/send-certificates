import enum
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(".env.local")


class CertificateFormat(enum.StrEnum):
    PNG = "png"
    PDF = "pdf"


MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.5  # seconds; doubles each attempt (exponential backoff on SES throttling)
SEND_CONCURRENCY = 10  # bounded concurrency for per-recipient sends (no queue needed at this volume)

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
FONTCONFIG_FILE = ASSETS_DIR / "fonts.conf"
EMAIL_TEMPLATE_PATH = ASSETS_DIR / "email_template.html"

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
