""" FastAPI Dependency Injection (get_db, get_session_repo)
"""
    
from typing import Any, Optional
from pydantic import BaseModel, Field

from dwg.domain.dsl import WorkflowDSLModel

# API Schemas
class StartSessionRequest(BaseModel):
    workflow_version_id: str = Field(..., description="THe immutable version ID of the workflow to execute", examples=["wf-v1"],)
    session_id: Optional[str] = Field(None, description="Optional client-provided unique session ID.", examples=["sess-100"],)
        
class StepSessionRequest(BaseModel):
    input: str = Field(..., description="The raw user submitted for the current turn.", examples=["James Grant"])

class SessionResponse(BaseModel):
    session_id: str
    workflow_version_id: str
    current_state_id: str
    status: str
    prompt: str
    is_terminal: bool
    collected_data: dict[str, Any]
    validation_error: Optional[str] = None


class RegisterDevWorkflowRequest(BaseModel):
    version_id: str = Field(..., examples=["wf-v1"])
    definition: WorkflowDSLModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


from functools import lru_cache
from dwg.engine.state_machine import WorkflowEngine
from dwg.engine.services.session_service import SessionService
from dwg.storage.redis_session import (InMemorySessionRepository, InMemoryWorkflowRepository)
from dwg.storage.repositories.interfaces import (WorkflowRepository, SessionRepository)

# API Dependencies
@lru_cache(maxsize=1)
def get_workflow_repository() -> WorkflowRepository:
    """ Singleton workflow repository for process lifetime.
    NOTE: In-memory sessions are lost upon process restart and not shared
    across multi-worker processes.
    """
    return InMemoryWorkflowRepository()

@lru_cache(maxsize=1)
def get_session_repository() -> SessionRepository:
    """Singleton session repository for process lifetime."""
    return InMemorySessionRepository()


def get_workflow_engine() -> WorkflowEngine:
    return WorkflowEngine()


def get_session_service() -> SessionService:
    return SessionService(
        engine=get_workflow_engine(),
        session_repository=get_session_repository(),
        workflow_repository=get_workflow_repository(),
    )