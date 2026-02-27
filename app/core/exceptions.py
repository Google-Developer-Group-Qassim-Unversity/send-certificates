from typing import Any, Optional


class AppError(Exception):
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(message)


class ValidationError(AppError):
    pass


class InvalidInputError(ValidationError):
    pass


class PreconditionsFailedError(ValidationError):
    pass


class DatabaseError(AppError):
    pass


class RecordNotFoundError(DatabaseError):
    def __init__(
        self, entity_type: str, identifier: Any, details: Optional[dict] = None
    ):
        super().__init__(
            message=f"{entity_type} with identifier '{identifier}' not found",
            error_code="RECORD_NOT_FOUND",
            details={
                "entity_type": entity_type,
                "identifier": str(identifier),
                **(details or {}),
            },
        )


class TransactionError(DatabaseError):
    pass


class CertificateError(AppError):
    pass


class TemplateNotFoundError(CertificateError):
    def __init__(self, template_path: str, details: Optional[dict] = None):
        super().__init__(
            message=f"Template file not found: {template_path}",
            error_code="TEMPLATE_NOT_FOUND",
            details={"template_path": template_path, **(details or {})},
        )


class PdfConversionError(CertificateError):
    pass


class CertificateGenerationError(CertificateError):
    pass


class EmailError(AppError):
    pass


class SmtpConnectionError(EmailError):
    pass


class EmailSendError(EmailError):
    def __init__(self, recipient: str, reason: str, details: Optional[dict] = None):
        super().__init__(
            message=f"Failed to send email to {recipient}: {reason}",
            error_code="EMAIL_SEND_FAILED",
            details={"recipient": recipient, "reason": reason, **(details or {})},
        )


class JobError(AppError):
    pass


class JobNotFoundError(RecordNotFoundError):
    def __init__(self, job_id: str):
        super().__init__("Job", job_id)


class EventNotFoundError(RecordNotFoundError):
    def __init__(self, event_id: int):
        super().__init__("Event", event_id)


class MemberNotFoundError(RecordNotFoundError):
    def __init__(self, member_id: int):
        super().__init__("Member", member_id)


class JobAlreadyProcessingError(JobError):
    def __init__(self, event_id: int, event_name: str):
        super().__init__(
            message=f"Event '{event_name}' (ID: {event_id}) is already being processed",
            error_code="JOB_ALREADY_PROCESSING",
            details={"event_id": event_id, "event_name": event_name},
        )
