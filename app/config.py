import enum
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(".env.local")


class EmailLogsFromAddress(enum.StrEnum):
    INFO_KERNELTICS = "info@kerneltics.com"
    GDG_QASSIM = "gdg.qu1@gmail.com"


class CertificateFormat(enum.StrEnum):
    PNG = "png"
    PDF = "pdf"


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
MAX_RETRIES = 3
EMAIL_DELAY = 4

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
FONTCONFIG_FILE = ASSETS_DIR / "fonts.conf"
EMAIL_TEMPLATE_PATH = ASSETS_DIR / "email_template.html"

APP_PASSWORDS: dict[EmailLogsFromAddress, str] = {
    EmailLogsFromAddress.INFO_KERNELTICS: os.getenv("APP_PASSWORD_KERNELTICS", ""),
    EmailLogsFromAddress.GDG_QASSIM: os.getenv("APP_PASSWORD_GDG_QASSIM", ""),
}

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")

missing = [k.value for k, v in APP_PASSWORDS.items() if not v]
if missing:
    raise ValueError(f"Missing app passwords for: {', '.join(missing)}")
