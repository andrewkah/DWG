from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from dwg.api.middleware.exception_handlers import (
    concurrency_conflict_handler,
    generic_dwg_error_handler,
    request_validation_exception_handler,
    session_not_found_handler,
    session_terminated_handler,
    unhandled_exception_handler,
    workflow_version_not_found_handler,
)
from dwg.api.v1.router import dev_router
from dwg.api.v1.sessions import router as sessions_router
from dwg.api.v1.ussd import ussd_router
from dwg.domain.errors import (
    ConcurrencyConflictError,
    DWGError,
    SessionNotFoundError,
    SessionTerminatedError,
    WorkflowVersionNotFoundError,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dynamic Workflow Gateway (DWG) API",
        version="1.0.0",
        description="Domain-nuetral workflow execution platform (REST & USSD)",
    )
    # Resgiter Exception Handlers
    app.add_exception_handler(SessionNotFoundError, session_not_found_handler)
    app.add_exception_handler(
        WorkflowVersionNotFoundError, workflow_version_not_found_handler
    )
    app.add_exception_handler(SessionTerminatedError, session_terminated_handler)
    app.add_exception_handler(ConcurrencyConflictError, concurrency_conflict_handler)
    app.add_exception_handler(
        RequestValidationError, request_validation_exception_handler
    )
    app.add_exception_handler(DWGError, generic_dwg_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Mount v1 Routers
    app.include_router(sessions_router, prefix="/api/v1")
    app.include_router(dev_router, prefix="/api/v1")
    app.include_router(ussd_router, prefix="/api/v1")

    return app


app = create_app()


@app.get("/")
async def root():
    return {"message": "Hello World"}
