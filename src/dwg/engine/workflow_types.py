"""Engine command & result interfaces"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    session_id: str
    current_state_id: str
    workflow_version_id: str
    status: str = "ACTIVE"  # ACTIVE, COMPLETED, CANCELLED, FAILED
    collected_data: dict[str, Any] = field(default_factory=dict)
    row_version: int = 1


@dataclass
class EngineResult:
    session: SessionState
    prompt: str
    comment: str | None = None
    is_terminal: bool = False
    validation_error: str | None = None
