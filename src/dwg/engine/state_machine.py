""" State transition & condition evaluation engine
"""

from dataclasses import dataclass

from dwg.domain.dsl import WorkflowDSLModel

class WorkflowEngine:
    """ Handles the core workflow dynamically """
    
    def __init__(self, max_transitions: int = 50):
        self.max_transitions = max_transitions
        
    def start_session(self, definition: WorkflowDSLModel, session_id: str, verison_id: str) -> EngineResult:
        """ Initializes a new session at the start_state """