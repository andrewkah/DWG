""" Domain exception (ValidationError, StateMismatchError)
"""

class DWGError(Exception):
    """ Base domain exception for all DWG runtime errors
    """
    pass

class SessionNotFoundError(DWGError):
    """ Custom error for an missing session
    """
    def __init__(self, session_id: str):
        super().__init__(f"session with ID '{session_id}' was not found")
        self.session_id = session_id
        

class WorkflowVersionNotFoundError(DWGError):
    """ Custom error for a missing workflow version
    """
    def __init__(self, version_id: str):
        super().__init__(f"Workflow version '{version_id}' not found")
        self.version_id = version_id

class SessionTerminatedError(DWGError):
    """ Custom error for a terminated session
    """
    def __init__(self, session_id: str, status: str):
        super().__init_(f"Cannot execute turn: Session '{session_id}' is already in status '{status}'")
        self.session_id = session_id
        self.status = status
        
class ConcurrencyConflictError(DWGError):
    """ Error handling for a conflict between sessions
    """
    def __init__(self, session_id: str, expected_version: int, actual_version: int):
        super().__init__(f"Concurrency conflict on session '{session_id}': expected row_version {expected_version}, but found {actual_version}.")
        self.session_id = session_id
        self.expected_version = expected_version
        self.actual_version = actual_version
