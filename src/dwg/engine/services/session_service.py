
from dwg.domain.dsl import WorkflowDSLModel
from dwg.engine.state_machine import WorkflowEngine
from dwg.domain.errors import SessionNotFoundError, SessionTerminatedError
from dwg.engine.types import EngineResult, SessionState
from dwg.storage.repositories.interfaces import SessionRepository, WorkflowRepository


class SessionService:
    def __init__(self, engine: WorkflowEngine, session_repository: SessionRepository, workflow_repository: WorkflowRepository):
        self.engine = engine
        self.sessions = session_repository
        self.workflows = workflow_repository
        
    def start(self, definition: WorkflowDSLModel, session_id: str, version_id: str,) -> EngineResult:
        """ Starts a new session, registers its pinned version, and persists initial state.
        """
        # 1. Execute engine start
        result = self.engine.start_session(
            definition=definition,
            session_id=session_id,
            version_id=version_id,
        )

        # 2. Persist newly created session
        self.sessions.create(result.session)
        return result
    
    def get_session(self, session_id: str) -> SessionState:
        """ Retrieves active session state or raises SessionNotFoundError.
        """
        session = self.sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session
    
    def execute(
        self,
        session_id: str,
        raw_input: str,
    ) -> EngineResult:
        """ Coordinates a single turn of user interaction.
        """
        # Load active session
        session = self.get_session(session_id)

        # Guard against executing turns on terminated sessions
        if session.status != "ACTIVE":
            raise SessionTerminatedError(session_id, session.status)

        # Capture expected version before executing for OCC check
        expected_version = session.row_version

        # Resolve the pinned workflow version
        definition = self.workflows.get_version(session.workflow_version_id)

        # Delegate pure state transition to the Workflow Engine
        result = self.engine.execute_turn(
            definition=definition,
            session=session,
            raw_input=raw_input,
        )

        # Atomically persist updated session
        self.sessions.update(
            session=result.session, expected_version=expected_version
        )

        # Return latest session state with incremented row_version
        result.session.row_version = expected_version + 1
        return result

    def cancel(self, session_id: str) -> EngineResult:
        """ Explicitly cancels an in-flight session.
        """
        session = self.get_session(session_id)
        if session.status != "ACTIVE":
            raise SessionTerminatedError(session_id, session.status)

        expected_version = session.row_version
        session.status = "CANCELLED"

        self.sessions.update(session=session, expected_version=expected_version)
        session.row_version = expected_version + 1

        return EngineResult(
            session=session,
            prompt="Session has been cancelled.",
            is_terminal=True,
        )
    