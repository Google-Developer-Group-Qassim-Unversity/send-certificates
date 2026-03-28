#!/usr/bin/env python3
"""
Interactive CLI for sending blast email campaigns.

Usage:
    python send-campaign.py

Features:
    - Fuzzy search campaign selection
    - Arrow key navigation
    - CSV or file input for emails
    - Real-time progress updates
"""

import sys
import re
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import questionary
from questionary import Style

from config import settings
from services import CampaignService, process_blast_job
from storage import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

CUSTOM_STYLE = Style(
    [
        ("qmark", "fg:cyan bold"),
        ("question", "bold"),
        ("answer", "fg:green bold"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:green bold"),
        ("separator", "fg:gray"),
        ("instruction", "fg:gray"),
        ("text", "fg:white"),
    ]
)

FILES_FOLDER = Path("files")


def get_available_campaigns() -> list[str]:
    """Get list of available campaign names."""
    campaigns_folder = Path(settings.campaigns_folder)
    if not campaigns_folder.exists():
        return []
    
    campaigns = []
    for campaign_dir in campaigns_folder.iterdir():
        if campaign_dir.is_dir():
            template_path = campaign_dir / "index.html"
            if template_path.exists():
                campaigns.append(campaign_dir.name)
    
    return sorted(campaigns)


def parse_emails_from_text(text: str) -> list[str]:
    """Parse emails from text (comma, newline, or space separated)."""
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    emails = re.findall(email_pattern, text)
    return list(dict.fromkeys(emails))


def parse_emails_from_file(filename: str) -> Optional[list[str]]:
    """Parse emails from a file."""
    file_path = FILES_FOLDER / filename
    
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return parse_emails_from_text(content)
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return None


def select_campaign() -> Optional[str]:
    """Interactive campaign selection with fuzzy search."""
    campaigns = get_available_campaigns()
    
    if not campaigns:
        print("\n❌ No campaigns found!")
        print("   Create a campaign in campaigns/ folder with index.html")
        return None
    
    return questionary.select(
        "Select a campaign:",
        choices=campaigns,
        style=CUSTOM_STYLE,
        use_jk_keys=False,
        use_search_filter=True,
    ).ask()


def select_input_method() -> Optional[str]:
    """Select email input method."""
    return questionary.select(
        "How do you want to provide emails?",
        choices=[
            questionary.Choice("📄 CSV - Enter comma-separated emails", value="csv"),
            questionary.Choice("📁 File - Load from files/ folder", value="file"),
        ],
        style=CUSTOM_STYLE,
    ).ask()


def get_emails_from_csv() -> Optional[list[str]]:
    """Get emails from CSV input."""
    while True:
        text = questionary.text(
            "Enter emails (comma or space separated):",
            style=CUSTOM_STYLE,
        ).ask()
        
        if text is None:
            return None
        
        emails = parse_emails_from_text(text)
        
        if not emails:
            print("❌ No valid emails found. Please try again.\n")
            continue
        
        return emails


def get_emails_from_file() -> Optional[list[str]]:
    """Get emails from a file."""
    files = sorted([f.name for f in FILES_FOLDER.iterdir() if f.is_file() and f.name != ".gitkeep"])
    
    if not files:
        print("\n❌ No files found in files/ folder!")
        print("   Add email files to the files/ folder")
        return None
    
    choices = [questionary.Choice(f"📄 {f}", value=f) for f in files]
    choices.append(questionary.Choice("✏️  Enter filename manually", value="manual"))
    
    selected = questionary.select(
        "Select a file:",
        choices=choices,
        style=CUSTOM_STYLE,
    ).ask()
    
    if selected is None:
        return None
    
    filename = selected
    if selected == "manual":
        filename = questionary.text(
            "Enter filename:",
            style=CUSTOM_STYLE,
        ).ask()
        
        if filename is None:
            return None
    
    emails = parse_emails_from_file(filename)
    
    if emails is None:
        print(f"\n❌ File '{filename}' not found in files/ folder")
        return None
    
    return emails


def get_subject(campaign_name: str) -> Optional[str]:
    """Get email subject from user."""
    default_subject = f"{campaign_name}"
    return questionary.text(
        f"Email subject (default: {default_subject}):",
        default=default_subject,
        style=CUSTOM_STYLE,
    ).ask()


def get_preview_text() -> Optional[str]:
    """Get preview text from user."""
    return questionary.text(
        "Preview text (optional, shown before opening email):",
        default="",
        style=CUSTOM_STYLE,
    ).ask()


def confirm_send(campaign_name: str, email_count: int, subject: str) -> bool:
    """Confirm before sending."""
    return questionary.confirm(
        f"Send to {email_count} recipients?\n  Campaign: {campaign_name}\n  Subject: {subject}",
        default=False,
        style=CUSTOM_STYLE,
    ).ask()


def print_summary(campaign_name: str, emails: list[str], successful: int, failed: int):
    """Print final summary."""
    total = len(emails)
    print("\n" + "═" * 50)
    print("📊 SUMMARY")
    print("═" * 50)
    print(f"  Campaign: {campaign_name}")
    print(f"  Total emails: {total}")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print("═" * 50 + "\n")


def main():
    """Main entry point."""
    print("\n" + "═" * 50)
    print("🚀 CAMPAIGN SENDER CLI")
    print("═" * 50 + "\n")
    
    FILES_FOLDER.mkdir(exist_ok=True)
    
    campaign_name = select_campaign()
    if campaign_name is None:
        print("\n👋 Cancelled.")
        sys.exit(0)
    
    input_method = select_input_method()
    if input_method is None:
        print("\n👋 Cancelled.")
        sys.exit(0)
    
    print()
    
    emails = []
    if input_method == "csv":
        emails = get_emails_from_csv()
    elif input_method == "file":
        emails = get_emails_from_file()
    
    if emails is None:
        print("\n👋 Cancelled.")
        sys.exit(0)
    
    print(f"\n📧 Found {len(emails)} unique emails")
    
    print("\n" + "─" * 30)
    print("📧 Email Settings")
    print("─" * 30)
    
    subject = get_subject(campaign_name)
    if subject is None:
        print("\n👋 Cancelled.")
        sys.exit(0)
    
    preview_text = get_preview_text()
    if preview_text is None:
        print("\n👋 Cancelled.")
        sys.exit(0)
    
    preview_display = preview_text if preview_text else "(none)"
    
    print(f"\n📋 Subject: {subject}")
    print(f"📋 Preview: {preview_display}")
    
    if not confirm_send(campaign_name, len(emails), subject):
        print("\n👋 Cancelled.")
        sys.exit(0)
    
    print("\n🚀 Starting campaign...")
    print("─" * 30)
    
    job_id = str(uuid.uuid4())
    folder_name = storage.create_job_folder(f"blast-{campaign_name}", job_id)
    
    storage.mark_event_processing(campaign_name, job_id)
    storage.initialize_job_status(
        job_id=job_id,
        event_name=campaign_name,
        folder_name=folder_name,
        total_members=len(emails),
    )
    
    process_blast_job(
        job_id=job_id,
        campaign_name=campaign_name,
        emails=emails,
        folder_name=folder_name,
        subject=subject if subject else None,
        preview_text=preview_text if preview_text else None,
    )
    
    summary = storage.read_blast_summary(folder_name)
    
    if summary:
        print_summary(
            campaign_name=campaign_name,
            emails=emails,
            successful=summary.successful,
            failed=summary.failed,
        )
    else:
        print("\n❌ Failed to get job summary")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Error: {e}")
        sys.exit(1)