""" REST session execution (/v1/sessions)
"""
import uuid
from fastapi import APIRouter, Depends, Response, status
from dwg.api.schemas_and_dependencies import (get_session_service, get_workflow_repository)
from dwg.api.schemas_and_dependencies import (StartSessionRequest, SessionResponse, StepSessionRequest, ErrorEnvelope)
from dwg.engine.services.session_service import SessionService
from dwg.domain.errors import WorkflowVersionNotFoundError
from dwg.storage.repositories.interfaces import WorkflowRepository


router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED, responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope},},)

def start_session(body: StartSessionRequest, response: Response, service: SessionService = Depends(get_session_service), workflow_repo: WorkflowRepository = Depends(get_workflow_repository),):
    """ Starts a session pinned to an eligible workflow version."""
    definition = workflow_repo.get_version(body.workflow_version_id)
    if not definition:
        raise WorkflowVersionNotFoundError(body.workflow_version_id)
    
    session_id = body.session_id or f"sess-{uuid.uuid4().hex[:12]}"
    exec_result = service.start(definition=definition, session_id=session_id, version_id=body.workflow_version_id,)

    return SessionResponse(
        session_id=exec_result.session.session_id,
        workflow_version_id=exec_result.session.workflow_version_id,
        current_state_id=exec_result.session.current_state_id,
        status=exec_result.session.status,
        prompt=exec_result.prompt,
        is_terminal=exec_result.is_terminal,
        collected_data=exec_result.session.collected_data,
        validation_error=exec_result.validation_error,
    )

@router.post(
    "/{session_id}/steps",
    response_model=SessionResponse,
    responses={
        200: {"model": SessionResponse},
        400: {"model": ErrorEnvelope},
        404: {"model": ErrorEnvelope},
        409: {"model": ErrorEnvelope},
        422: {"model": SessionResponse, "description": "Validation error during workflow step"},
    },
)
def submit_session_step(session_id: str, body: StepSessionRequest, response: Response, service: SessionService = Depends(get_session_service),):
    """ Submits input to advance an existing session.
    Returns 200 on valid state transition, or 422 if input fails workflow validation rules.
    """
    exec_result = service.execute(session_id=session_id, input=body.input)

    if exec_result.validation_error is not None:
        response.status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    else:
        response.status_code = status.HTTP_200_OK

    return SessionResponse(
        session_id=exec_result.session.session_id,
        workflow_version_id=exec_result.session.workflow_version_id,
        current_state_id=exec_result.session.current_state_id,
        status=exec_result.session.status,
        prompt=exec_result.prompt,
        is_terminal=exec_result.is_terminal,
        collected_data=exec_result.session.collected_data,
        validation_error=exec_result.validation_error,
    )

@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    responses={
        404: {"model": ErrorEnvelope}
    },
)
def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
):
    """ Retrieves current session state and prompt.
    """
    session = service.get_session(session_id)
    definition = workflow_repo.get_version(session.workflow_version_id)

    # Resolve active prompt
    active_state = next(s for s in definition.states if s.id == session.current_state_id)
    
    return SessionResponse(
        session_id=session.session_id,
        workflow_version_id=session.workflow_version_id,
        current_state_id=session.current_state_id,
        status=session.status,
        prompt=active_state.prompt.default,
        is_terminal=(session.status != "ACTIVE"),
        collected_data=session.collected_data,
        validation_error=None,
    )

    