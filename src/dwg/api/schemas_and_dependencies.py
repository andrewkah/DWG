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
 