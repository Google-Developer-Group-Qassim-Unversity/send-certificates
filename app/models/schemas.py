from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum


class Gender(str, Enum):
    male = "Male"
    female = "Female"


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class RecipientStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class JobType(str, Enum):
    certificate = "certificate"
    reminder = "reminder"
    notification = "notification"
    custom = "custom"


class TemplateType(str, Enum):
    official = "official"
    unofficial = "unofficial"


class CertificateRequest(BaseModel):
    event_id: int
    member_ids: list[int]

    @field_validator("member_ids")
    @classmethod
    def check_members_not_empty(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("member_ids list cannot be empty")
        return v


class JobProgress(BaseModel):
    total: int
    completed: int
    successful: int
    failed: int


class JobResponse(BaseModel):
    job_id: str
    event_id: int
    event_name: str
    job_type: JobType
    status: JobStatus
    progress: JobProgress
    created_at: datetime
    updated_at: datetime


class RecipientResult(BaseModel):
    recipient_id: int
    member_id: int
    name: str
    email: Optional[str]
    status: RecipientStatus
    sent_at: Optional[datetime] = None
    certificate_url: Optional[str] = None
    error: Optional[str] = None


class JobDetailResponse(BaseModel):
    job_id: str
    event_id: int
    event_name: str
    job_type: JobType
    status: JobStatus
    progress: JobProgress
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    recipients: list[RecipientResult]


class JobListItem(BaseModel):
    job_id: str
    event_id: int
    event_name: str
    job_type: JobType
    status: JobStatus
    progress: JobProgress
    created_at: datetime


class JobsListResponse(BaseModel):
    total: int
    jobs: list[JobListItem]


class HealthCheck(BaseModel):
    status: str
    libreoffice: str
    smtp: str
    timestamp: datetime
