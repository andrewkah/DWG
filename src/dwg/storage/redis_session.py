import copy
from typing import Optional
from dwg.domain.dsl import WorkflowDefinition
from dwg.domain.errors import (
    ConcurrencyConflictError,
    SessionNotFoundError,
    WorkflowVersionNotFoundError,
)
from dwg.engine.types import SessionState
from dwg.storage.repositories.interfaces import SessionRepository, WorkflowRepository


class InMemorySessionRepository(SessionRepository):

    def __init__(self):
        self._sessions: dict[str, SessionState] = {}

    def create(self, session: SessionState) -> None:
        # Deepcopy simulates serializing to external storage
        self._sessions[session.session_id] = copy.deepcopy(session)

    def get(self, session_id: str) -> Optional[SessionState]:
        session = self._sessions.get(session_id)
        return copy.deepcopy(session) if session else None

    def update(self, session: SessionState, expected_version: int) -> None:
        current = self._sessions.get(session.session_id)
        if not current:
            raise SessionNotFoundError(session.session_id)

        # Optimistic locking check
        if current.row_version != expected_version:
            raise ConcurrencyConflictError(
                session_id=session.session_id,
                expected_version=expected_version,
                actual_version=current.row_version,
            )

        # Increment version on atomic write
        updated_session = copy.deepcopy(session)
        updated_session.row_version = expected_version + 1
        self._sessions[session.session_id] = updated_session


class InMemoryWorkflowRepository(WorkflowRepository):

    def __init__(self):
        self._definitions: dict[str, WorkflowDefinition] = {}

    def get_version(self, version_id: str) -> Optional[WorkflowDefinition]:
        definition = self._definitions.get(version_id)
        if not definition:
            raise WorkflowVersionNotFoundError(version_id)
        return copy.deepcopy(definition)

    def save_version(
        self, version_id: str, definition: WorkflowDefinition
    ) -> None:
        self._definitions[version_id] = copy.deepcopy(definition)