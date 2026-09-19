from enum import Enum, auto
from typing import Dict, Tuple, Callable, Any

class State(Enum):
    DRAFT = auto()
    UNDER_REVIEW = auto()
    APPROVED = auto()
    REJECTED = auto()
    PUBLISHED = auto()

class Action(Enum):
    SUBMIT = auto()
    APPROVE = auto()
    REJECT = auto()
    PUBLISH = auto()
    REVERT = auto()
    
# Transition Table: (Current State, Action) -> Next State
TRANSITION_TABLE: Dict[Tuple[State, Action], State] = {
    (State.DRAFT, Action.SUBMIT): State.UNDER_REVIEW,
    
    (State.UNDER_REVIEW, Action.APPROVE): State.APPROVED,
    (State.UNDER_REVIEW, Action.REJECT): State.REJECTED,
    
    (State.REJECTED, Action.REVERT): State.DRAFT,
    
    (State.APPROVED, Action.PUBLISH): State.PUBLISHED,
    (State.APPROVED, Action.REVERT): State.DRAFT,
}

class WorkflowException(Exception):
    """Raised when an invalid transition is attempted."""
    pass

def get_next_state(current_state: State, action: Action) -> State:
    """
    Pure transition function: f(S, A) -> S'
    Derives the next state based on the current state and action.
    """
    next_state = TRANSITION_TABLE.get((current_state, action))
    
    if not next_state:
        raise WorkflowException(
            f"Invalid transition: Cannot perform action '{action.name}' on state '{current_state.name}'"
        )
        
    return next_state

class WorkflowEngine:
    def __init__(self, initial_state: State = State.DRAFT):
        self.state = initial_state

    def trigger(self, action: Action, *args: Any, **kwargs: Any) -> State:
        """Validates, transitions state, and handles execution side-effects."""
        # 1. Derive next state using our pure transition function
        target_state = get_next_state(self.state, action)
        
        # 2. Execute side effects hook (e.g., logging or event dispatching)
        self._on_transition(self.state, action, target_state)
        
        # 3. Commit state change
        self.state = target_state
        return self.state

    def _on_transition(self, source: State, action: Action, target: State):
        print(f"[Workflow] Transitioned successfully: {source.name} --({action.name})--> {target.name}")

# --- Example Usage ---
if __name__ == "__main__":
    engine = WorkflowEngine()  # Starts at DRAFT
    
    # Valid flow
    engine.trigger(Action.SUBMIT)   # Moves to UNDER_REVIEW
    engine.trigger(Action.APPROVE)  # Moves to APPROVED
    engine.trigger(Action.PUBLISH)  # Moves to PUBLISHED
    
    # Invalid flow attempt
    try:
        engine.trigger(Action.APPROVE)  # Cannot approve a published document
    except WorkflowException as e:
        print(f"[Error] {e}")
