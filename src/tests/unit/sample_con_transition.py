# A real-world Document Approval Workflow map
WORKFLOW_TRANSITIONS = {
    "DRAFT": {
        "SUBMIT": {
            "to": "UNDER_REVIEW",
            "guards": [lambda ctx: ctx.get("has_content", False)],
            "actions": [lambda ctx: print("Notification: Document submitted for review.")]
        }
    },
    "UNDER_REVIEW": {
        "APPROVE": {
            "to": "APPROVED",
            "guards": [lambda ctx: ctx.get("approver_role") == "MANAGER"],
            "actions": [lambda ctx: print("Notification: Document was approved!")]
        },
        "REJECT": {
            "to": "DRAFT",
            "guards": [],
            "actions": [lambda ctx: print("Notification: Document sent back to draft.")]
        }
    },
    "APPROVED": {}  # Terminal state (No valid transitions out)
}

class WorkflowEngine:
    def __init__(self, transition_map: dict, initial_state: str):
        self.transitions = transition_map
        self.current_state = initial_state

    def can_transition(self, event: str, context: dict) -> tuple[bool, str]:
        """
        Derives if a transition is legal without actually altering state.
        Returns (is_allowed, reason_or_destination)
        """
        # 1. Check if the current state has any transitions mapped
        state_transitions = self.transitions.get(self.current_state)
        if not state_transitions:
            return False, f"State '{self.current_state}' is a terminal state."

        # 2. Check if the specific event/trigger exists for this state
        transition_rule = state_transitions.get(event)
        if not transition_rule:
            return False, f"Invalid event '{event}' from state '{self.current_state}'."

        # 3. Evaluate guard functions (All must return True)
        for guard in transition_rule.get("guards", []):
            if not guard(context):
                return False, f"Guard condition failed for event '{event}'."

        return True, transition_rule["to"]

    def transition(self, event: str, context: dict) -> str:
        """
        The core transition function. Executes state change and actions.
        """
        allowed, result = self.can_transition(event, context)
        
        if not allowed:
            raise ValueError(f"Transition Denied: {result}")
        
        target_state = result
        transition_rule = self.transitions[self.current_state][event]

        # Execute side-effect actions before shifting state safely 
        for action in transition_rule.get("actions", []):
            try:
                action(context)
            except Exception as e:
                # In production, handle action failures (rollback or fail transition)
                raise RuntimeError(f"Action failed during transition: {e}")

        # Finalize state update
        print(f"Transition Success: {self.current_state} -> {target_state}")
        self.current_state = target_state
        return self.current_state


# Context simulating state variables or user metadata
context_data = {
    "has_content": True,
    "approver_role": "EMPLOYEE"  # Notice this is not a Manager!
}

# Initialize engine
engine = WorkflowEngine(WORKFLOW_TRANSITIONS, initial_state="DRAFT")

# 1. Submit the document
engine.transition("SUBMIT", context_data) 
# Output: Notification: Document submitted for review.
# Output: Transition Success: DRAFT -> UNDER_REVIEW

# 2. Try to approve it as a regular employee (Should fail guard check)
try:
    engine.transition("APPROVE", context_data)
except ValueError as e:
    print(e) 
    # Output: Transition Denied: Guard condition failed for event 'APPROVE'.

# 3. Elevate user privileges in context and retry
context_data["approver_role"] = "MANAGER"
engine.transition("APPROVE", context_data)
# Output: Notification: Document was approved!
# Output: Transition Success: UNDER_REVIEW -> APPROVED
