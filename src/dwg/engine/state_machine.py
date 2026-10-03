"""State transition & condition evaluation engine"""

from dataclasses import dataclass

from dwg.domain.dsl import WorkflowDSLModel, StateModel
from dwg.engine.types import EngineResult, SessionState
from dwg.engine.validator import ConditionEvaluator, InputValidator


class WorkflowEngine:
    """Handles the core workflow dynamically"""

    def __init__(self, max_transitions: int = 50):
        self.max_transitions = max_transitions

    def start_session(
        self, definition: WorkflowDSLModel, session_id: str, version_id: str
    ) -> EngineResult:
        """Initializes a new session at the start_state"""
        start_state = definition.get_state(definition.start_state)
        is_terminal = start_state.kind == "terminal"
        initial_status = (start_state.terminal_status or "COMPLETED") if is_terminal else "ACTIVE"
        initial_session = SessionState(
            session_id=session_id,
            current_state_id=start_state.id,
            workflow_version_id=version_id,
            status=initial_status,
            collected_data={},
        )
        return EngineResult(
            session=initial_session,
            prompt=start_state.prompt.default,
            is_terminal=is_terminal,
        )

    def _resolve_next_state(
        self, current_state: StateModel, collected_data: dict
    ) -> str | None:
        """Retrieve the next corresponding state"""
        if not current_state.transitions:
            return None
        for transition in current_state.transitions:
            if transition.condition is None:
                return transition.next
            if ConditionEvaluator.evaluate_operator_and_value_fit(
                transition.condition, collected_data
            ):
                return transition.next
        return None

    def execute_turn(
        self, definition: WorkflowDSLModel, session: SessionState, input: str
    ) -> EngineResult:
        """Interpret/execute a single step in the workflow"""
        if session.status != "ACTIVE":
            return EngineResult(
                session=session,
                prompt="Session is no longer active!",
                is_terminal=True,
            )

        current_state = definition.get_state(session.current_state_id)
        # Work on the Input request
        if current_state.kind == "input" and current_state.field:
            is_valid, raw_string, message = InputValidator.validate_and_coerce(
                current_state.field, input
            )
            if not is_valid:
                error_prompt = f"{message}\n{current_state.prompt.default}"
                return EngineResult(
                    session=session,
                    prompt=error_prompt,
                    is_terminal=(current_state.kind == "terminal"),
                )
            # save session data
            session.collected_data[current_state.field.name] = raw_string

        # Work on the Confirm request
        elif current_state.kind == "confirm":
            # True=confirm, False=Cancel
            if input == False:
                session.status = "CANCELLED"
                return EngineResult(
                    session=session, prompt="Task cancelled!", is_terminal=True
                )
        # Transition selection
        next_state_id = self._resolve_next_state(
            current_state=current_state, collected_data=session.collected_data
        )
        if not next_state_id:
            session.status = "FAILED"
            return EngineResult(
                session=session,
                prompt="System error: No valid transition path found!",
                is_terminal=True,
            )

        # Advance state
        next_state = definition.get_state(next_state_id)
        session.current_state_id = next_state.id
        # session.transition_count += 1
        # session.row_version += 1

        # Work on the Terminal state
        if next_state.kind == "terminal":
            session.status = next_state.terminal_status or "COMPLETED"
            return EngineResult(
                session=session,
                prompt=next_state.prompt.default,
                is_terminal=True,
            )

        return EngineResult(
            session=session,
            prompt=next_state.prompt.default,
            is_terminal=(next_state.kind == "terminal"),
        )
