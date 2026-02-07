import os
from platform import system
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# ============ CONFIGURATION VARIABLES ============

# Environment: production or development (default: production)
ENVIRONMENT = os.getenv("ENVIRONMENT", "production").lower()

# Email settings (required from .env)
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
if not APP_PASSWORD:
    raise ValueError("APP_PASSWORD environment variable is required in .env file")

# Email configuration
SENDER_EMAIL = "gdg.qu1@gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# Certificate templates
OFFICIAL_TEMPLATE = "certificate.pptx"
UNOFFICIAL_TEMPLATE = "certificate unofficial.pptx"
EMAIL_TEMPLATE = "index.html"

# Processing settings
MAX_RETRIES = 3
EMAIL_DELAY = 4

# Placeholders
DELIMITER_START = "<<"
DELIMITER_END = ">>"
NAME_PLACEHOLDER = "name"
EVENT_NAME_PLACEHOLDER = "event_name"
DATE_PLACEHOLDER = "event_date"

# PDF conversion
CONVERSION_EXTENSION = "pdf"

# LibreOffice path (auto-detect based on OS)
if system() == "Windows":
    LIBREOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"
else:
    LIBREOFFICE_PATH = "libreoffice"

# Storage - environment-specific
if ENVIRONMENT == "production":
    JOBS_FOLDER = str(Path.home() / "GDG-certificates")
    # Create folder if it doesn't exist
    Path(JOBS_FOLDER).mkdir(parents=True, exist_ok=True)
else:  # development
    JOBS_FOLDER = "jobs"


# ============ SETTINGS CLASS (for backward compatibility) ============


class Settings:
    environment = ENVIRONMENT
    app_password = APP_PASSWORD
    sender_email = SENDER_EMAIL
    smtp_host = SMTP_HOST
    smtp_port = SMTP_PORT
    official_template = OFFICIAL_TEMPLATE
    unofficial_template = UNOFFICIAL_TEMPLATE
    email_template = EMAIL_TEMPLATE
    max_retries = MAX_RETRIES
    email_delay = EMAIL_DELAY
    jobs_folder = JOBS_FOLDER
    delimiter_start = DELIMITER_START
    delimiter_end = DELIMITER_END
    name_placeholder = NAME_PLACEHOLDER
    event_name_placeholder = EVENT_NAME_PLACEHOLDER
    date_placeholder = DATE_PLACEHOLDER
    conversion_extension = CONVERSION_EXTENSION
    libreoffice_path = LIBREOFFICE_PATH

    def get_libreoffice_path(self) -> str:
        """Get LibreOffice executable path."""
        return self.libreoffice_path


settings = Settings()
