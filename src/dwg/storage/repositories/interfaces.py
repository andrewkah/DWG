

from abc import ABC, abstractmethod
from typing import Optional

from dwg.domain.dsl import WorkflowDSLModel
from dwg.engine.types import SessionState


class SessionRepository(ABC):
    @abstractmethod
    def create(self, session: SessionState) -> None:
        """ Persists a new active session.
        """
        pass
    
    @abstractmethod
    def get(self, session_id: str) -> Optional[SessionState]:
        """ Retrieves a session by its ID, returning None if not found or expired.
        """
        pass
    
    @abstractmethod
    def update(self, session: SessionState, expected_version: int) -> None:
        """ Updates an existing session if and only if its current row_version matched expected_version.
            Raises ConcurrencyConflictError on version mismatch.
        """
        pass
    
class WorkflowRepository(ABC):
    @abstractmethod
    def get_version(self, vrsion_id: str) -> Optional[WorkflowDSLModel]:
        """ Retrieves the immutable workflow definition for a specific version.
        """
        pass
    
    @abstractmethod
    def save_version(self, version_id: str, definition: WorkflowDSLModel) -> None:
        """ Saves a published workflow definition version.
        """
        pass
    