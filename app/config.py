import enum
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class EmailLogsFromAddress(str, enum.Enum):
    INFO_KERNELTICS = "info@kerneltics.com"
    GDG_QASSIM = "gdg.qu1@gmail.com"


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

missing = [k.value for k, v in APP_PASSWORDS.items() if not v]
if missing:
    raise ValueError(f"Missing app passwords for: {', '.join(missing)}")
