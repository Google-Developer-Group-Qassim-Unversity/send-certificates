"""
Manual certificate sender - Send test certificates without running FastAPI server.

This script allows you to send test certificates directly by importing functions
from the existing codebase and executing them without needing to start the server.
"""

from pathlib import Path
from datetime import datetime
from config import settings
from models import Member, Gender
from services import CertificateService


def send_test_certificate(
    name: str,
    email: str,
    event_name: str,
    announced_name: str,
    date: str,
    official: bool = True,
    gender: Gender = Gender.male,
) -> bool:
    """
    Send a single test certificate directly.

    Args:
        name: Recipient's name (used in certificate)
        email: Recipient's email address
        event_name: Event name for the certificate
        announced_name: Announced/registered name for email body
        date: Event date (e.g., "2026-02-08")
        official: Whether to use official template (default: True)
        gender: Recipient's gender (default: Gender.male)

    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n{'=' * 60}")
    print(f"Sending certificate to: {name} ({email})")
    print(f"Event: {event_name}")
    print(f"Date: {date}")
    print(f"Template: {'Official' if official else 'Unofficial'}")
    print(f"{'=' * 60}\n")

    # Initialize service
    service = CertificateService()

    # Check dependencies
    print("🔍 Checking dependencies...")
    if not service.check_smtp():
        print("❌ SMTP not configured properly")
        print("   Make sure APP_PASSWORD is set in .env file")
        return False

    if not service.check_libreoffice():
        print("❌ LibreOffice not available")
        print("   Install LibreOffice or check the path in config.py")
        return False

    print("✅ All dependencies are available\n")

    # Create output folder
    output_folder = Path("test-output-files")
    output_folder.mkdir(exist_ok=True)
    print(f"📁 Output folder: {output_folder.absolute()}\n")

    try:
        # Get template
        print("📄 Loading certificate template...")
        template_path = service.get_template_path(official)
        print(f"   Template: {template_path}\n")

        # Generate PPTX with placeholders replaced
        print("✏️  Generating personalized certificate...")
        pptx_path = service.replace_placeholder(
            name=name,
            event_name=event_name,
            date=date,
            template_path=template_path,
            output_folder=output_folder,
        )
        print(f"   PPTX created: {pptx_path.name}\n")

        # Convert to PDF
        print("📄 Converting to PDF...")
        pdf_path = service.pptx_to_pdf(pptx_path, output_folder)

        if pdf_path is None:
            print("❌ PDF conversion failed")
            print("   Check LibreOffice installation and permissions")
            return False

        print(f"   PDF created: {pdf_path.name}\n")

        # Send email
        print("📧 Sending email...")
        success, error = service.send_email(
            recipient=email,
            name=name,
            event_name=event_name,
            announced_name=announced_name,
            pdf_path=pdf_path,
        )

        if success:
            print(f"✅ Certificate successfully sent to {email}\n")
            print(f"📁 Files saved in: {output_folder.absolute()}")
            return True
        else:
            print(f"❌ Failed to send email: {error}\n")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}\n")
        return False


def send_multiple_certificates(
    members: list[dict],
    event_name: str,
    announced_name: str,
    date: str,
    official: bool = True,
) -> dict:
    """
    Send certificates to multiple recipients.

    Args:
        members: List of dicts with keys: name, email, gender
        event_name: Event name for certificates
        announced_name: Announced/registered name for email body
        date: Event date
        official: Whether to use official template

    Returns:
        dict: Summary with counts of successful/failed sends
    """
    results = {"success": 0, "failed": 0, "total": len(members)}

    print(f"\n{'=' * 60}")
    print(f"Sending {len(members)} certificates")
    print(f"{'=' * 60}\n")

    for i, member_data in enumerate(members, 1):
        print(f"\n[{i}/{len(members)}] Processing {member_data['name']}...")

        success = send_test_certificate(
            name=member_data["name"],
            email=member_data["email"],
            event_name=event_name,
            announced_name=announced_name,
            date=date,
            official=official,
            gender=member_data.get("gender", Gender.male),
        )

        if success:
            results["success"] += 1
        else:
            results["failed"] += 1

        # Add delay between sends (as per original code)
        if i < len(members):
            import time

            print("\n⏳ Waiting 4 seconds before next send...")
            time.sleep(4)

    print(f"\n{'=' * 60}")
    print(f"📊 Summary:")
    print(f"   Total: {results['total']}")
    print(f"   ✅ Success: {results['success']}")
    print(f"   ❌ Failed: {results['failed']}")
    print(f"{'=' * 60}\n")

    return results


if __name__ == "__main__":
    # Example 1: Send a single test certificate
    print("Example 1: Single Certificate Test\n")

    send_test_certificate(
        name="Test User",
        email="albrrak337@gmail.com",  # Replace with your email for testing
        event_name="Test Event 2026",
        announced_name="Test Event Official Name",
        date="2026-02-08",
        official=True,
        gender=Gender.male,
    )

    # Example 2: Send to multiple recipients (commented out by default)
    # Uncomment to send to multiple people at once
    """
    print("\n\nExample 2: Multiple Recipients Test\n")
    
    test_recipients = [
        {
            "name": "Test User 1",
            "email": "gdg.qu1@gmail.com",
            "gender": Gender.male
        },
        {
            "name": "مرت على بالي",
            "email": "albrrak337@gmail.com",
            "gender": Gender.male
        },
        {
            "name": "عبدالاله عبدالعزيز منصور البراك",
            "email": "albrrak773@gmail.com",
            "gender": Gender.male
        },
    ]
    
    send_multiple_certificates(
        members=test_recipients,
        event_name="Workshop 2026",
        announced_name="Advanced Development Workshop",
        date="2026-02-08",
        official=True,
    )
    """
