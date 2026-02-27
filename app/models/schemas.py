from pydantic import BaseModel, EmailStr, model_validator
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
    certificate_event = "certificate_event"
    certificate_custom = "certificate_custom"
    email_blast = "email_blast"
    reminder = "reminder"
    notification = "notification"


class TemplateType(str, Enum):
    official = "official"
    unofficial = "unofficial"


class BlastDeliveryStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    partial = "partial"
    failed = "failed"


class CertificateRequest(BaseModel):
    event_id: int
    member_ids: list[int]

    @model_validator(mode="after")
    def check_members_not_empty(self):
        if not self.member_ids:
            raise ValueError("member_ids list cannot be empty")
        return self


class CustomCertificateRecipient(BaseModel):
    name: str
    email: EmailStr
    custom_data: Optional[dict] = None


class CustomCertificateRequest(BaseModel):
    event_name: str
    event_date: str
    official: bool
    recipients: list[CustomCertificateRecipient]
    event_id: Optional[int] = None

    @model_validator(mode="after")
    def check_recipients_not_empty(self):
        if not self.recipients:
            raise ValueError("recipients list cannot be empty")
        return self

    @model_validator(mode="after")
    def check_not_empty(self):
        if not self.event_name or not self.event_name.strip():
            raise ValueError("event_name cannot be empty")
        if not self.event_date or not self.event_date.strip():
            raise ValueError("event_date cannot be empty")
        return self


class EmailBlastRecipientRef(BaseModel):
    member_id: Optional[int] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None

    @model_validator(mode="after")
    def check_at_least_one(self):
        if not self.member_id and not self.email:
            raise ValueError("Either member_id or email must be provided")
        return self


class EmailBlastRequest(BaseModel):
    subject: str
    body_html: str
    body_text: Optional[str] = None
    is_templated: bool = False
    recipients: list[EmailBlastRecipientRef]
    event_id: Optional[int] = None

    @model_validator(mode="after")
    def check_recipients_not_empty(self):
        if not self.recipients:
            raise ValueError("recipients list cannot be empty")
        return self

    @model_validator(mode="after")
    def check_not_empty(self):
        if not self.subject or not self.subject.strip():
            raise ValueError("subject cannot be empty")
        if not self.body_html or not self.body_html.strip():
            raise ValueError("body_html cannot be empty")
        return self


class JobProgress(BaseModel):
    total: int
    completed: int
    successful: int
    failed: int


class JobResponse(BaseModel):
    job_id: str
    event_id: Optional[int]
    event_name: str
    job_type: JobType
    status: JobStatus
    progress: JobProgress
    created_at: datetime
    updated_at: datetime


class RecipientResult(BaseModel):
    recipient_id: int
    member_id: Optional[int]
    name: str
    email: Optional[str]
    status: RecipientStatus
    sent_at: Optional[datetime] = None
    certificate_url: Optional[str] = None
    error: Optional[str] = None


class JobDetailResponse(BaseModel):
    job_id: str
    event_id: Optional[int]
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
    event_id: Optional[int]
    event_name: str
    job_type: JobType
    status: JobStatus
    progress: JobProgress
    created_at: datetime


class JobsListResponse(BaseModel):
    total: int
    jobs: list[JobListItem]


class FailedRecipient(BaseModel):
    email: str
    name: Optional[str] = None
    error: Optional[str] = None


class EmailBlastResponse(BaseModel):
    job_id: str
    event_id: Optional[int]
    event_name: str
    subject: str
    is_templated: bool
    delivery_status: BlastDeliveryStatus
    sent_count: int
    failed_count: int
    total_recipients: int
    created_at: datetime
    sent_at: Optional[datetime] = None


class EmailBlastDetailResponse(BaseModel):
    job_id: str
    event_id: Optional[int]
    event_name: str
    subject: str
    body_html: str
    body_text: Optional[str]
    is_templated: bool
    delivery_status: BlastDeliveryStatus
    sent_count: int
    failed_count: int
    total_recipients: int
    failed_recipients: Optional[list[FailedRecipient]] = None
    created_at: datetime
    sent_at: Optional[datetime] = None


class EmailBlastListItem(BaseModel):
    job_id: str
    event_id: Optional[int]
    event_name: str
    subject: str
    delivery_status: BlastDeliveryStatus
    sent_count: int
    failed_count: int
    total_recipients: int
    created_at: datetime


class EmailBlastListResponse(BaseModel):
    total: int
    blasts: list[EmailBlastListItem]


class HealthCheck(BaseModel):
    status: str
    libreoffice: str
    smtp: str
    timestamp: datetime
