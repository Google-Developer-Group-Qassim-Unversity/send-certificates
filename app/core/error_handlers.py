import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.exceptions import (
    AppError,
    ValidationError,
    RecordNotFoundError,
    JobNotFoundError,
    EventNotFoundError,
    MemberNotFoundError,
    JobAlreadyProcessingError,
    CertificateError,
    TemplateNotFoundError,
    PdfConversionError,
    EmailError,
    DatabaseError,
    TransactionError,
)

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        status_code = _get_status_code_for_error(exc)

        logger.error(
            f"AppError: {exc.error_code} - {exc.message}",
            extra={
                "error_code": exc.error_code,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method,
            },
        )

        content: dict[str, Any] = {
            "error_code": exc.error_code,
            "message": exc.message,
            **({"details": exc.details} if exc.details else {}),
        }

        return JSONResponse(
            status_code=status_code,
            content=content,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

        logger.warning(
            f"Validation error on {request.method} {request.url.path}: {errors}",
            extra={"errors": errors, "path": request.url.path},
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": errors},
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            f"Unhandled exception on {request.method} {request.url.path}: {exc}",
            extra={"path": request.url.path, "method": request.method},
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )


def _get_status_code_for_error(exc: AppError) -> int:
    if isinstance(
        exc,
        (
            RecordNotFoundError,
            JobNotFoundError,
            EventNotFoundError,
            MemberNotFoundError,
        ),
    ):
        return status.HTTP_404_NOT_FOUND

    if isinstance(exc, JobAlreadyProcessingError):
        return status.HTTP_409_CONFLICT

    if isinstance(exc, ValidationError):
        return status.HTTP_400_BAD_REQUEST

    if isinstance(exc, TemplateNotFoundError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, (PdfConversionError, CertificateError)):
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, EmailError):
        return status.HTTP_502_BAD_GATEWAY

    if isinstance(exc, TransactionError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, DatabaseError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    return status.HTTP_500_INTERNAL_SERVER_ERROR
