from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum


class Gender(str, Enum):
    male = "male"
    female = "female"


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class MemberStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


# ============ Request Models ============


class Member(BaseModel):
    name: str
    email: EmailStr
    gender: Gender


class CertificateRequest(BaseModel):
    event_name: str
    announced_name: str
    date: str
    official: bool
    members: list[Member]

    @field_validator("members")
    @classmethod
    def check_members_not_empty(cls, v: list[Member]) -> list[Member]:
        if not v:
            raise ValueError("Members list cannot be empty")
        return v

    @field_validator("event_name", "announced_name", "date")
    @classmethod
    def check_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


# ============ Response Models ============


class CertificateResponse(BaseModel):
    job_id: str
    event_name: str
    folder_name: str
    status: JobStatus
    message: str


class JobProgress(BaseModel):
    total: int
    completed: int
    successful: int
    failed: int


class JobStatusResponse(BaseModel):
    job_id: str
    event_name: str
    folder_name: str
    status: JobStatus
    progress: JobProgress
    created_at: datetime
    updated_at: datetime


class MemberResult(BaseModel):
    name: str
    email: str
    gender: str
    status: MemberStatus
    sent_at: Optional[datetime] = None
    certificate_url: Optional[str] = None
    error: Optional[str] = None


class JobSummary(BaseModel):
    job_id: str
    event_name: str
    announced_name: str
    folder_name: str
    date: str
    official: bool
    created_at: datetime
    completed_at: Optional[datetime] = None
    status: JobStatus
    total_members: int
    successful: int
    failed: int
    members: list[MemberResult]


class EventListItem(BaseModel):
    folder_name: str
    event_name: str
    announced_name: str
    date: str
    created_at: datetime
    status: JobStatus
    total_members: int
    successful: int
    failed: int


class EventsList(BaseModel):
    total: int
    events: list[EventListItem]


class HealthCheck(BaseModel):
    status: str
    libreoffice: str
    smtp: str
    timestamp: datetime
