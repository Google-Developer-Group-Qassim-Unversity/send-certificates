from typing import Optional
import datetime
import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    text,
)
from sqlalchemy.dialects.mysql import ENUM, INTEGER, TEXT, TINYINT, VARCHAR
from sqlmodel import Field, Relationship, SQLModel


class ActionsActionType(str, enum.Enum):
    COMPOSITE = "composite"
    DEPARTMENT = "department"
    MEMBER = "member"
    BONUS = "bonus"


class DepartmentsType(str, enum.Enum):
    ADMINISTRATIVE = "administrative"
    PRACTICAL = "practical"


class EventsLocationType(str, enum.Enum):
    ONLINE = "online"
    ON_SITE = "on-site"
    NONE = "none"
    HIDDEN = "hidden"


class EventsStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    ACTIVE = "active"
    CLOSED = "closed"


class FormsFormType(str, enum.Enum):
    NONE = "none"
    REGISTRATION = "registration"
    GOOGLE = "google"


class MembersGender(str, enum.Enum):
    MALE = "Male"
    FEMALE = "Female"


class ModificationsType(str, enum.Enum):
    BONUS = "bonus"
    DISCOUNT = "discount"


class RoleRole(str, enum.Enum):
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    NONE = "none"


class SubmissionsSubmissionType(str, enum.Enum):
    NONE = "none"
    REGISTRATION = "registration"
    PARTIAL = "partial"
    GOOGLE = "google"


class Actions(SQLModel, table=True):
    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    action_name: str = Field(
        sa_column=Column("action_name", VARCHAR(60), nullable=False)
    )
    points: int = Field(sa_column=Column("points", INTEGER, nullable=False))
    action_type: ActionsActionType = Field(
        sa_column=Column(
            "action_type",
            Enum(
                ActionsActionType,
                values_callable=lambda cls: [member.value for member in cls],
            ),
            nullable=False,
        )
    )
    ar_action_name: str = Field(
        sa_column=Column("ar_action_name", VARCHAR(100), nullable=False)
    )

    logs: list["Logs"] = Relationship(back_populates="action")


class Departments(SQLModel, table=True):
    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    name: str = Field(sa_column=Column("name", String(50), nullable=False))
    type: DepartmentsType = Field(
        sa_column=Column(
            "type",
            Enum(
                DepartmentsType,
                values_callable=lambda cls: [member.value for member in cls],
            ),
            nullable=False,
        )
    )
    ar_name: str = Field(sa_column=Column("ar_name", VARCHAR(100), nullable=False))

    departments_logs: list["DepartmentsLogs"] = Relationship(
        back_populates="department"
    )


class Events(SQLModel, table=True):
    __table_args__ = (Index("event_name", "name"), Index("events_id_IDX", "id", "name"))

    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    name: str = Field(sa_column=Column("name", VARCHAR(150), nullable=False))
    location_type: EventsLocationType = Field(
        sa_column=Column(
            "location_type",
            Enum(
                EventsLocationType,
                values_callable=lambda cls: [member.value for member in cls],
            ),
            nullable=False,
        )
    )
    location: str = Field(sa_column=Column("location", VARCHAR(100), nullable=False))
    start_datetime: datetime.datetime = Field(
        sa_column=Column(
            "start_datetime",
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    end_datetime: datetime.datetime = Field(
        sa_column=Column(
            "end_datetime",
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    status: EventsStatus = Field(
        sa_column=Column(
            "status",
            Enum(
                EventsStatus,
                values_callable=lambda cls: [member.value for member in cls],
            ),
            nullable=False,
        )
    )
    description: Optional[str] = Field(
        default=None, sa_column=Column("description", TEXT)
    )
    image_url: Optional[str] = Field(
        default=None, sa_column=Column("image_url", VARCHAR(100))
    )
    is_official: Optional[int] = Field(
        default=None,
        sa_column=Column("is_official", TINYINT(1), server_default=text("'0'")),
    )

    forms: list["Forms"] = Relationship(back_populates="event")
    logs: list["Logs"] = Relationship(back_populates="event")


class Members(SQLModel, table=True):
    __table_args__ = (Index("uni_id", "uni_id", unique=True),)

    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    name: str = Field(sa_column=Column("name", String(50), nullable=False))
    uni_id: str = Field(sa_column=Column("uni_id", String(50), nullable=False))
    gender: MembersGender = Field(
        sa_column=Column(
            "gender",
            Enum(
                MembersGender,
                values_callable=lambda cls: [member.value for member in cls],
            ),
            nullable=False,
        )
    )
    uni_level: int = Field(sa_column=Column("uni_level", Integer, nullable=False))
    uni_college: str = Field(
        sa_column=Column("uni_college", VARCHAR(100), nullable=False)
    )
    created_at: datetime.datetime = Field(
        sa_column=Column(
            "created_at",
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: datetime.datetime = Field(
        sa_column=Column(
            "updated_at",
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    is_authenticated: int = Field(
        sa_column=Column(
            "is_authenticated", TINYINT(1), nullable=False, server_default=text("'0'")
        )
    )
    email: Optional[str] = Field(default=None, sa_column=Column("email", String(100)))
    phone_number: Optional[str] = Field(
        default=None, sa_column=Column("phone_number", String(20))
    )

    role: list["Role"] = Relationship(back_populates="member")
    members_logs: list["MembersLogs"] = Relationship(back_populates="member")
    submissions: list["Submissions"] = Relationship(back_populates="member")


class Forms(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="forms_ibfk_1",
        ),
        Index("forms_unique_event_id", "event_id", unique=True),
    )

    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    event_id: int = Field(sa_column=Column("event_id", INTEGER, nullable=False))
    form_type: FormsFormType = Field(
        sa_column=Column(
            "form_type",
            Enum(
                FormsFormType,
                values_callable=lambda cls: [member.value for member in cls],
            ),
            nullable=False,
        )
    )
    google_form_id: Optional[str] = Field(
        default=None, sa_column=Column("google_form_id", VARCHAR(100))
    )
    google_refresh_token: Optional[str] = Field(
        default=None, sa_column=Column("google_refresh_token", VARCHAR(500))
    )
    google_watch_id: Optional[str] = Field(
        default=None, sa_column=Column("google_watch_id", String(100))
    )
    google_responders_url: Optional[str] = Field(
        default=None, sa_column=Column("google_responders_url", VARCHAR(150))
    )

    event: "Events" = Relationship(back_populates="forms")
    submissions: list["Submissions"] = Relationship(back_populates="form")


class Logs(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["action_id"],
            ["actions.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="logs_ibfk_1",
        ),
        ForeignKeyConstraint(
            ["event_id"], ["events.id"], ondelete="CASCADE", name="fk_events"
        ),
        Index("action_id", "action_id"),
        Index("fk_events", "event_id"),
    )

    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    action_id: int = Field(sa_column=Column("action_id", INTEGER, nullable=False))
    event_id: Optional[int] = Field(default=None, sa_column=Column("event_id", INTEGER))

    action: "Actions" = Relationship(back_populates="logs")
    event: Optional["Events"] = Relationship(back_populates="logs")
    departments_logs: list["DepartmentsLogs"] = Relationship(back_populates="log")
    members_logs: list["MembersLogs"] = Relationship(back_populates="log")
    modifications: list["Modifications"] = Relationship(back_populates="log")


class Role(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_role_member",
        ),
        Index("fk_role_member", "member_id"),
    )

    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    member_id: int = Field(sa_column=Column("member_id", INTEGER, nullable=False))
    role: RoleRole = Field(
        sa_column=Column(
            "role",
            Enum(
                RoleRole, values_callable=lambda cls: [member.value for member in cls]
            ),
            nullable=False,
        )
    )

    member: "Members" = Relationship(back_populates="role")


class DepartmentsLogs(SQLModel, table=True):
    __tablename__ = "departments_logs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="departments_logs_departments_FK",
        ),
        ForeignKeyConstraint(
            ["log_id"],
            ["logs.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="departments_logs_logs_FK",
        ),
        Index("departments_logs_departments_FK", "department_id"),
        Index("departments_logs_idx", "log_id", "department_id"),
    )

    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    department_id: int = Field(
        sa_column=Column("department_id", INTEGER, nullable=False)
    )
    log_id: int = Field(sa_column=Column("log_id", INTEGER, nullable=False))

    department: "Departments" = Relationship(back_populates="departments_logs")
    log: "Logs" = Relationship(back_populates="departments_logs")


class MembersLogs(SQLModel, table=True):
    __tablename__ = "members_logs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["log_id"],
            ["logs.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="members_logs_logs_FK",
        ),
        ForeignKeyConstraint(["member_id"], ["members.id"], name="fk_members_id"),
        Index("fk_members_id", "member_id"),
        Index("idx_members_logs_log_id", "log_id"),
        Index("unique_member_log_day", "member_id", "log_id", "date", unique=True),
    )

    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    member_id: int = Field(sa_column=Column("member_id", INTEGER, nullable=False))
    log_id: int = Field(sa_column=Column("log_id", INTEGER, nullable=False))
    date: datetime.datetime = Field(
        sa_column=Column(
            "date", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
        )
    )

    log: "Logs" = Relationship(back_populates="members_logs")
    member: "Members" = Relationship(back_populates="members_logs")


class Modifications(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["log_id"],
            ["logs.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="modifications_ibfk_1",
        ),
        Index("log_id", "log_id"),
    )

    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    log_id: int = Field(sa_column=Column("log_id", INTEGER, nullable=False))
    type: ModificationsType = Field(
        sa_column=Column(
            "type",
            Enum(
                ModificationsType,
                values_callable=lambda cls: [member.value for member in cls],
            ),
            nullable=False,
        )
    )
    value: int = Field(sa_column=Column("value", INTEGER, nullable=False))

    log: "Logs" = Relationship(back_populates="modifications")


class Submissions(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(
            ["form_id"],
            ["forms.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="submissions_ibfk_1",
        ),
        ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="submissions_ibfk_2",
        ),
        Index("from_id_member_id_idx", "form_id", "member_id"),
        Index("submissions_unique", "member_id", "form_id", unique=True),
    )

    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    form_id: int = Field(sa_column=Column("form_id", INTEGER, nullable=False))
    member_id: int = Field(sa_column=Column("member_id", INTEGER, nullable=False))
    is_accepted: int = Field(
        sa_column=Column(
            "is_accepted", TINYINT(1), nullable=False, server_default=text("'0'")
        )
    )
    submitted_at: datetime.datetime = Field(
        sa_column=Column(
            "submitted_at",
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    submission_type: SubmissionsSubmissionType = Field(
        sa_column=Column(
            "submission_type",
            Enum(
                SubmissionsSubmissionType,
                values_callable=lambda cls: [member.value for member in cls],
            ),
            nullable=False,
        )
    )
    google_submission_id: Optional[str] = Field(
        default=None, sa_column=Column("google_submission_id", String(100))
    )
    google_submission_value: Optional[dict] = Field(
        default=None, sa_column=Column("google_submission_value", JSON)
    )

    form: "Forms" = Relationship(back_populates="submissions")
    member: "Members" = Relationship(back_populates="submissions")


class EmailServiceJobType(str, enum.Enum):
    CERTIFICATE = "certificate"
    REMINDER = "reminder"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


class EmailServiceJobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EmailServiceRecipientStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class EmailServiceTemplateType(str, enum.Enum):
    OFFICIAL = "official"
    UNOFFICIAL = "unofficial"


class EmailServiceJob(SQLModel, table=True):
    __tablename__ = "email_service_jobs"
    __table_args__ = (Index("email_service_jobs_event_id", "event_id"),)

    id: str = Field(sa_column=Column("id", VARCHAR(36), primary_key=True))
    event_id: int = Field(sa_column=Column("event_id", INTEGER, nullable=False))
    job_type: EmailServiceJobType = Field(
        sa_column=Column(
            "job_type",
            Enum(
                EmailServiceJobType,
                values_callable=lambda cls: [member.value for member in cls],
            ),
            nullable=False,
        )
    )
    status: EmailServiceJobStatus = Field(
        sa_column=Column(
            "status",
            Enum(
                EmailServiceJobStatus,
                values_callable=lambda cls: [member.value for member in cls],
            ),
            nullable=False,
            server_default="'pending'",
        )
    )
    total: int = Field(
        sa_column=Column("total", INTEGER, nullable=False, server_default="'0'")
    )
    completed: int = Field(
        sa_column=Column("completed", INTEGER, nullable=False, server_default="'0'")
    )
    successful: int = Field(
        sa_column=Column("successful", INTEGER, nullable=False, server_default="'0'")
    )
    failed: int = Field(
        sa_column=Column("failed", INTEGER, nullable=False, server_default="'0'")
    )
    created_at: datetime.datetime = Field(
        sa_column=Column(
            "created_at",
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: datetime.datetime = Field(
        sa_column=Column(
            "updated_at",
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        )
    )
    completed_at: Optional[datetime.datetime] = Field(
        default=None, sa_column=Column("completed_at", DateTime)
    )

    recipients: list["EmailServiceRecipient"] = Relationship(back_populates="job")


class EmailServiceRecipient(SQLModel, table=True):
    __tablename__ = "email_service_recipients"
    __table_args__ = (
        ForeignKeyConstraint(
            ["job_id"],
            ["email_service_jobs.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="email_service_recipients_job_fk",
        ),
        ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="email_service_recipients_member_fk",
        ),
        Index("email_service_recipients_job_id", "job_id"),
        Index("email_service_recipients_member_id", "member_id"),
        Index("email_service_recipients_unique", "job_id", "member_id", unique=True),
    )

    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    job_id: str = Field(sa_column=Column("job_id", VARCHAR(36), nullable=False))
    member_id: int = Field(sa_column=Column("member_id", INTEGER, nullable=False))
    status: EmailServiceRecipientStatus = Field(
        sa_column=Column(
            "status",
            Enum(
                EmailServiceRecipientStatus,
                values_callable=lambda cls: [member.value for member in cls],
            ),
            nullable=False,
            server_default="'pending'",
        )
    )
    sent_at: Optional[datetime.datetime] = Field(
        default=None, sa_column=Column("sent_at", DateTime)
    )
    error: Optional[str] = Field(default=None, sa_column=Column("error", TEXT))

    job: "EmailServiceJob" = Relationship(back_populates="recipients")
    member: "Members" = Relationship()
    certificate: Optional["EmailServiceCertificate"] = Relationship(
        back_populates="recipient"
    )


class EmailServiceCertificate(SQLModel, table=True):
    __tablename__ = "email_service_certificates"
    __table_args__ = (
        ForeignKeyConstraint(
            ["recipient_id"],
            ["email_service_recipients.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="email_service_certificates_recipient_fk",
        ),
        Index("email_service_certificates_recipient_id", "recipient_id", unique=True),
    )

    id: int = Field(sa_column=Column("id", INTEGER, primary_key=True))
    recipient_id: int = Field(sa_column=Column("recipient_id", INTEGER, nullable=False))
    certificate_path: str = Field(
        sa_column=Column("certificate_path", VARCHAR(500), nullable=False)
    )
    template_type: EmailServiceTemplateType = Field(
        sa_column=Column(
            "template_type",
            Enum(
                EmailServiceTemplateType,
                values_callable=lambda cls: [member.value for member in cls],
            ),
            nullable=False,
        )
    )

    recipient: "EmailServiceRecipient" = Relationship(back_populates="certificate")
