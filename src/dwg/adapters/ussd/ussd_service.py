"""Handles mapping between the telco and underlying Engine SessionService"""

import uuid

from dwg.adapters.ussd.base import (
    CanonicalUSSDRequest,
    CanonicalUSSDResponse,
    USSDAction,
)
from dwg.domain.errors import DWGError, SessionNotFoundError
from dwg.engine.services.session_service import SessionService
from dwg.storage.repositories.interfaces import WorkflowRepository


class ShortCodeNotBoundError(DWGError):
    def __init__(self, service_code: str):
        super().__init__(f"Service code '{service_code}' is not bound to any active workflow.")
        self.service_code = service_code


class UssdChannelService:
    def __init__(
        self,
        session_service: SessionService,
        workflow_repository: WorkflowRepository,
    ):
        self.session_service = session_service
        self.workflow_repository = workflow_repository
        # In-memory mapping for this milestone (provider, provider_session_id) -> internal session_id
        self._correlations: dict[tuple[str, str], str] = {}
        # service_code -> workflow_version_id
        self._bindings: dict[str, str] = {}

    def bind_shortcode(self, service_code: str, workflow_version_id: str) -> None:
        """Binds a dailed short code to a specific published workflow version."""
        self._bindings[service_code] = workflow_version_id

    def handle_turn(self, req: CanonicalUSSDRequest) -> CanonicalUSSDResponse:
        correlation_key = (req.provider, req.provider_session_id)
        internal_session_id = self._correlations.get(correlation_key)

        # INITIAL DIAL-IN
        if req.is_new_session or internal_session_id is None:
            version_id = self._bindings.get(req.service_code)
            if not version_id:
                return CanonicalUSSDResponse(
                    action=USSDAction.END,
                    message="Service code not configured. Please check and try again.",
                )
            definition = self.workflow_repository.get_version(version_id)
            if not definition:
                return CanonicalUSSDResponse(
                    action=USSDAction.END,
                    message="Service temporarily unavailable.",
                )

            # Generate the unique internal session Id
            internal_session_id = f"ussd-{uuid.uuid4().hex[:12]}"
            self._correlations[correlation_key] = internal_session_id

            exec_result = self.session_service.start(
                definition=definition,
                session_id=internal_session_id,
                version_id=version_id,
            )
            # If the start is already terminal (rare)
            if exec_result.is_terminal:
                self._correlations.pop(correlation_key, None)
                return CanonicalUSSDResponse(action=USSDAction.END, message=exec_result.prompt)
            return CanonicalUSSDResponse(action=USSDAction.CON, message=exec_result.prompt)

        # SUBSEQUENT INPUT TURNS
        try:
            exec_result = self.session_service.execute(session_id=internal_session_id, input=req.raw_input)
        except SessionNotFoundError:
            # Session expired from in-memory cache
            self._correlations.pop(correlation_key, None)
            return CanonicalUSSDResponse(
                action=USSDAction.END,
                message="Your session has expired. Please Dial again.",
            )
        except Exception:
            self._correlations.pop(correlation_key, None)
            return CanonicalUSSDResponse(
                action=USSDAction.END,
                message="An unexpected system error occurred. Please try again later.",
            )

        # TERMINAL CHECK
        if exec_result.is_terminal:
            # Cleanup correlation mapping
            self._correlations.pop(correlation_key, None)
            return CanonicalUSSDResponse(action=USSDAction.END, message=exec_result.prompt)

        # Continue Interaction
        return CanonicalUSSDResponse(action=USSDAction.CON, message=exec_result.prompt)
