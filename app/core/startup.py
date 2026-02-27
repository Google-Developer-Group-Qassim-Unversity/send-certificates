import logging
import subprocess
from pathlib import Path
from typing import NamedTuple

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

logger = logging.getLogger(__name__)


class StartupCheck(NamedTuple):
    name: str
    passed: bool
    message: str


def validate_startup() -> list[StartupCheck]:
    checks: list[StartupCheck] = []

    checks.append(_check_official_template())
    checks.append(_check_unofficial_template())
    checks.append(_check_email_template())
    checks.append(_check_libreoffice())
    checks.append(_check_certificates_folder())
    checks.append(_check_database_connection())

    failures = [c for c in checks if not c.passed]

    if failures:
        logger.error("=" * 60)
        logger.error("STARTUP VALIDATION FAILED")
        logger.error("=" * 60)
        for check in failures:
            logger.error(f"  ❌ {check.name}: {check.message}")
        logger.error("=" * 60)
    else:
        logger.info("Startup validation passed - all checks OK")

    return checks


def _check_official_template() -> StartupCheck:
    template_path = Path(settings.official_template)
    if template_path.exists():
        return StartupCheck(
            name="Official Template",
            passed=True,
            message=f"Found at {template_path}",
        )
    return StartupCheck(
        name="Official Template",
        passed=False,
        message=f"Not found at {template_path}",
    )


def _check_unofficial_template() -> StartupCheck:
    template_path = Path(settings.unofficial_template)
    if template_path.exists():
        return StartupCheck(
            name="Unofficial Template",
            passed=True,
            message=f"Found at {template_path}",
        )
    return StartupCheck(
        name="Unofficial Template",
        passed=False,
        message=f"Not found at {template_path}",
    )


def _check_email_template() -> StartupCheck:
    template_path = Path(settings.email_template)
    if template_path.exists():
        return StartupCheck(
            name="Email Template",
            passed=True,
            message=f"Found at {template_path}",
        )
    return StartupCheck(
        name="Email Template",
        passed=False,
        message=f"Not found at {template_path}",
    )


def _check_libreoffice() -> StartupCheck:
    libreoffice_path = settings.get_libreoffice_path()
    try:
        result = subprocess.run(
            [libreoffice_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = (
                result.stdout.strip().split("\n")[0] if result.stdout else "unknown"
            )
            return StartupCheck(
                name="LibreOffice",
                passed=True,
                message=f"Available ({version})",
            )
        return StartupCheck(
            name="LibreOffice",
            passed=False,
            message=f"Command failed with code {result.returncode}",
        )
    except FileNotFoundError:
        return StartupCheck(
            name="LibreOffice",
            passed=False,
            message=f"Executable not found at {libreoffice_path}",
        )
    except subprocess.TimeoutExpired:
        return StartupCheck(
            name="LibreOffice",
            passed=False,
            message="Command timed out",
        )
    except Exception as e:
        return StartupCheck(
            name="LibreOffice",
            passed=False,
            message=f"Error: {e}",
        )


def _check_certificates_folder() -> StartupCheck:
    folder_path = Path(settings.certificates_folder)
    try:
        folder_path.mkdir(parents=True, exist_ok=True)

        test_file = folder_path / ".write_test"
        test_file.write_text("test")
        test_file.unlink()

        return StartupCheck(
            name="Certificates Folder",
            passed=True,
            message=f"Writable at {folder_path}",
        )
    except PermissionError:
        return StartupCheck(
            name="Certificates Folder",
            passed=False,
            message=f"Permission denied: {folder_path}",
        )
    except Exception as e:
        return StartupCheck(
            name="Certificates Folder",
            passed=False,
            message=f"Error: {e}",
        )


def _check_database_connection() -> StartupCheck:
    try:
        from sqlmodel import Session

        with Session(engine) as session:
            session.exec(text("SELECT 1"))

        return StartupCheck(
            name="Database",
            passed=True,
            message="Connection successful",
        )
    except Exception as e:
        return StartupCheck(
            name="Database",
            passed=False,
            message=f"Connection failed: {e}",
        )


def get_startup_status() -> dict:
    checks = validate_startup()
    failures = [c for c in checks if not c.passed]

    return {
        "healthy": len(failures) == 0,
        "checks": [
            {
                "name": c.name,
                "passed": c.passed,
                "message": c.message,
            }
            for c in checks
        ],
    }
