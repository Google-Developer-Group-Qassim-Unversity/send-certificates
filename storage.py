import json
import re
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import settings
from models import (
    JobStatus,
    MemberStatus,
    MemberResult,
    JobSummary,
    EventListItem,
    Member,
)


class StorageManager:
    """Manages file-based storage for certificate jobs."""

    def __init__(self, jobs_folder: str = settings.jobs_folder):
        self.jobs_folder = Path(jobs_folder)
        self.jobs_folder.mkdir(exist_ok=True)

        # Track active jobs to prevent concurrent processing of same event
        self._active_jobs: dict[str, str] = {}  # {event_name: job_id}
        self._lock = threading.Lock()

        # Track in-memory job status for real-time updates
        self._job_status: dict[str, dict] = {}  # {job_id: status_dict}

    def sanitize_event_name(self, event_name: str) -> str:
        """Convert event name to safe folder name with timestamp."""
        # Remove or replace unsafe characters
        # Keep alphanumeric, Arabic chars, hyphens, underscores
        sanitized = re.sub(r"[^\w\s\u0600-\u06FF-]", "", event_name)
        # Replace spaces with hyphens
        sanitized = re.sub(r"\s+", "-", sanitized.strip())
        # Remove consecutive hyphens
        sanitized = re.sub(r"-+", "-", sanitized)
        # Limit length
        sanitized = sanitized[:50] if len(sanitized) > 50 else sanitized
        # Add timestamp
        timestamp = int(time.time())
        return f"{sanitized}-{timestamp}"

    def is_event_processing(self, event_name: str) -> bool:
        """Check if an event with the same name is currently being processed."""
        with self._lock:
            return event_name in self._active_jobs

    def get_active_job_id(self, event_name: str) -> Optional[str]:
        """Get the job ID of an active job for the given event name."""
        with self._lock:
            return self._active_jobs.get(event_name)

    def mark_event_processing(self, event_name: str, job_id: str) -> None:
        """Mark an event as currently processing."""
        with self._lock:
            self._active_jobs[event_name] = job_id

    def mark_event_completed(self, event_name: str) -> None:
        """Remove event from active processing list."""
        with self._lock:
            self._active_jobs.pop(event_name, None)

    def create_job_folder(self, event_name: str, job_id: str) -> str:
        """Create a folder for a new job and return the folder name."""
        folder_name = self.sanitize_event_name(event_name)
        folder_path = self.jobs_folder / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_name

    def get_job_folder_path(self, folder_name: str) -> Path:
        """Get the full path to a job folder."""
        return self.jobs_folder / folder_name

    def initialize_job_status(
        self,
        job_id: str,
        event_name: str,
        folder_name: str,
        total_members: int,
    ) -> None:
        """Initialize in-memory job status."""
        with self._lock:
            self._job_status[job_id] = {
                "job_id": job_id,
                "event_name": event_name,
                "folder_name": folder_name,
                "status": JobStatus.pending,
                "progress": {
                    "total": total_members,
                    "completed": 0,
                    "successful": 0,
                    "failed": 0,
                },
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

    def update_job_status(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        increment_completed: bool = False,
        increment_successful: bool = False,
        increment_failed: bool = False,
    ) -> None:
        """Update in-memory job status."""
        with self._lock:
            if job_id not in self._job_status:
                return

            job = self._job_status[job_id]
            if status:
                job["status"] = status
            if increment_completed:
                job["progress"]["completed"] += 1
            if increment_successful:
                job["progress"]["successful"] += 1
            if increment_failed:
                job["progress"]["failed"] += 1
            job["updated_at"] = datetime.utcnow().isoformat()

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Get in-memory job status."""
        with self._lock:
            return self._job_status.get(job_id)

    def write_summary(
        self,
        folder_name: str,
        job_id: str,
        event_name: str,
        date: str,
        official: bool,
        members: list[MemberResult],
        status: JobStatus,
        created_at: datetime,
        completed_at: Optional[datetime] = None,
    ) -> None:
        """Write or update summary.json file."""
        folder_path = self.get_job_folder_path(folder_name)
        summary_path = folder_path / "summary.json"

        successful = sum(1 for m in members if m.status == MemberStatus.sent)
        failed = sum(1 for m in members if m.status == MemberStatus.failed)

        summary_data = {
            "job_id": job_id,
            "event_name": event_name,
            "folder_name": folder_name,
            "date": date,
            "official": official,
            "created_at": created_at.isoformat(),
            "completed_at": completed_at.isoformat() if completed_at else None,
            "status": status.value,
            "total_members": len(members),
            "successful": successful,
            "failed": failed,
            "members": [m.model_dump() for m in members],
        }

        with self._lock:
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2, default=str)

    def read_summary(self, folder_name: str) -> Optional[JobSummary]:
        """Read summary.json from a job folder."""
        summary_path = self.get_job_folder_path(folder_name) / "summary.json"

        if not summary_path.exists():
            return None

        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Convert members to MemberResult objects
        members = [
            MemberResult(
                name=m["name"],
                email=m["email"],
                gender=m["gender"],
                status=MemberStatus(m["status"]),
                sent_at=datetime.fromisoformat(m["sent_at"])
                if m.get("sent_at")
                else None,
                certificate_url=m.get("certificate_url"),
                error=m.get("error"),
            )
            for m in data.get("members", [])
        ]

        return JobSummary(
            job_id=data["job_id"],
            event_name=data["event_name"],
            folder_name=data["folder_name"],
            date=data["date"],
            official=data["official"],
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
            status=JobStatus(data["status"]),
            total_members=data["total_members"],
            successful=data["successful"],
            failed=data["failed"],
            members=members,
        )

    def list_all_summaries(self) -> list[EventListItem]:
        """List all job summaries."""
        events = []

        if not self.jobs_folder.exists():
            return events

        for folder in self.jobs_folder.iterdir():
            if not folder.is_dir():
                continue

            summary_path = folder / "summary.json"
            if not summary_path.exists():
                continue

            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                events.append(
                    EventListItem(
                        folder_name=data["folder_name"],
                        event_name=data["event_name"],
                        date=data["date"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        status=JobStatus(data["status"]),
                        total_members=data["total_members"],
                        successful=data["successful"],
                        failed=data["failed"],
                    )
                )
            except (json.JSONDecodeError, KeyError):
                # Skip malformed summaries
                continue

        # Sort by created_at descending (newest first)
        events.sort(key=lambda x: x.created_at, reverse=True)
        return events

    def get_folder_by_job_id(self, job_id: str) -> Optional[str]:
        """Find folder name by job ID."""
        # First check in-memory status
        with self._lock:
            if job_id in self._job_status:
                return self._job_status[job_id].get("folder_name")

        # Fall back to scanning folders
        if not self.jobs_folder.exists():
            return None

        for folder in self.jobs_folder.iterdir():
            if not folder.is_dir():
                continue

            summary_path = folder / "summary.json"
            if not summary_path.exists():
                continue

            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("job_id") == job_id:
                    return folder.name
            except (json.JSONDecodeError, KeyError):
                continue

        return None

    def get_certificate_path(self, folder_name: str, filename: str) -> Optional[Path]:
        """Get the full path to a certificate file if it exists."""
        file_path = self.get_job_folder_path(folder_name) / filename
        if file_path.exists() and file_path.is_file():
            return file_path
        return None


# Global storage manager instance
storage = StorageManager()
