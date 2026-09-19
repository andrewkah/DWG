""" Engine command & result interfaces
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SessionState:
    session_id: str
    current_state_id: str
    workflow_version_id: str
    status: str = 'ACTIVE' # ACTIVE, COMPLETED, CANCELLED, FAILED
    collected_data: dict[str, Any] = field(default_factory=dict)
    
    

@dataclass
class EngineResult:    
    session: SessionState
    prompt: str
    comment: Optional[str]
    is_terminal: bool = False
    