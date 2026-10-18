"""Catch domain exceptions from Engine, map them into HTTP status codes and error responses"""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dwg.api.schemas_and_dependencies import ErrorDetail, ErrorEnvelope
from dwg.domain.errors import (
    ConcurrencyConflictError,
    DWGError,
    SessionNotFoundError,
    SessionTerminatedError,
    WorkflowVersionNotFoundError,
)


def create_error_response(
    status_code: int, code: str, message: str, details=None
) -> JSONResponse:
    payload = ErrorEnvelope(
        error=ErrorDetail(code=code, message=message, details=details)
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


async def session_not_found_handler(request: Request, exc: SessionNotFoundError):
    return create_error_response(
        status.HTTP_404_NOT_FOUND, "SESSION_NOT_FOUND", str(exc)
    )


async def workflow_version_not_found_handler(
    request: Request, exc: WorkflowVersionNotFoundError
):
    return create_error_response(
        status.HTTP_404_NOT_FOUND, "WORKFLOW_VERSION_NOT_FOUND", str(exc)
    )


async def session_terminated_handler(request: Request, exc: SessionTerminatedError):
    return create_error_response(
        status.HTTP_409_CONFLICT, "SESSION_ALREADY_TERMIANTED", str(exc)
    )


async def concurency_conflict_handler(request: Request, exc: ConcurrencyConflictError):
    return create_error_response(
        status.HTTP_409_CONFLICT, "COnCURENCY_CONFLICT", str(exc)
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    return create_error_response(
        status.HTTP_400_BAD_REQUEST,
        "MALFORMED_REQUEST_BODY",
        "The request body was missing required fields or malformed.",
        details=exc.errors(),
    )


async def generic_dwg_error_handler(request: Request, exc: DWGError):
    return create_error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR, "WORKFLOW_EXECUTION_ERROR", str(exc)
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    return create_error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_SERVER_ERROR",
        "An unexpected internal error occurred.",
    )
