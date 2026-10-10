import copy

import pytest
from dwg.domain.dsl import (
    ChoiceOptionModel,
    ConditionModel,
    FieldModel,
    FieldValidationModel,
    PromptModel,
    StateModel,
    TransitionModel,
    WorkflowDSLModel,
)
from dwg.domain.errors import (
    ConcurrencyConflictError,
    SessionNotFoundError,
    SessionTerminatedError,
)
from dwg.engine.state_machine import WorkflowEngine
from dwg.engine.services.session_service import SessionService
from dwg.storage.redis_session import (
    InMemorySessionRepository,
    InMemoryWorkflowRepository,
)


@pytest.fixture
def branching_workflow() -> WorkflowDSLModel:
    """Fixture defining: Name -> Age -> Employed? (Yes -> Employer | No -> Done) -> Done"""
    return WorkflowDSLModel(
        dsl_schema_version="1.0",
        workflow_id="kyc_onboarding",
        name="KYC Onboarding",
        start_state="name_step",
        states=[
            StateModel(
                id="name_step",
                kind="input",
                prompt=PromptModel(default="Enter full name:"),
                field=FieldModel(
                    name="full_name",
                    type="text",
                    required=True,
                    validation=FieldValidationModel(min_length=3),
                ),
                transitions=[TransitionModel(next="age_step")],
            ),
            StateModel(
                id="age_step",
                kind="input",
                prompt=PromptModel(default="Enter age:"),
                field=FieldModel(
                    name="age",
                    type="integer",
                    required=True,
                    validation=FieldValidationModel(min=18),
                ),
                transitions=[TransitionModel(next="employed_step")],
            ),
            StateModel(
                id="employed_step",
                kind="input",
                prompt=PromptModel(default="Are you employed?\n1. Yes\n2. No"),
                field=FieldModel(
                    name="employed",
                    type="choice",
                    required=True,
                    options=[
                        ChoiceOptionModel(label="Yes", value=True),
                        ChoiceOptionModel(label="No", value=False),
                    ],
                ),
                transitions=[
                    TransitionModel(
                        condition=ConditionModel(
                            field="employed", operator="equals", value=True
                        ),
                        next="employer_step",
                    ),
                    TransitionModel(
                        condition=ConditionModel(
                            field="employed", operator="equals", value=False
                        ),
                        next="complete_step",
                    ),
                ],
            ),
            StateModel(
                id="employer_step",
                kind="input",
                prompt=PromptModel(default="Enter employer name:"),
                field=FieldModel(name="employer", type="text", required=True),
                transitions=[TransitionModel(next="complete_step")],
            ),
            StateModel(
                id="complete_step",
                kind="terminal",
                terminal_status="COMPLETED",
                prompt=PromptModel(default="Registration complete! Thank you."),
            ),
        ],
    )


@pytest.fixture
def session_service(branching_workflow) -> SessionService:
    workflow_repo = InMemoryWorkflowRepository()
    session_repo = InMemorySessionRepository()

    # Register pinned workflow version
    workflow_repo.save_version(
        version_id="wf-v1", definition=branching_workflow
    )

    engine = WorkflowEngine()
    return SessionService(
        engine=engine,
        session_repository=session_repo,
        workflow_repository=workflow_repo,
    )


def test_full_orchestration_happy_path(session_service, branching_workflow):
    """Verifies that SessionService correctly drives the engine through a complete workflow."""
    # 1. Start Session
    res1 = session_service.start(
        definition=branching_workflow,
        session_id="sess-100",
        version_id="wf-v1",
    )
    assert res1.session.status == "ACTIVE"
    assert res1.session.current_state_id == "name_step"
    assert res1.session.row_version == 1
    assert res1.prompt == "Enter full name:"

    # 2. Enter Name (Turn 1)
    res2 = session_service.execute("sess-100", "Sarah Nabukeera")
    assert res2.session.current_state_id == "age_step"
    assert res2.session.collected_data["full_name"] == "Sarah Nabukeera"
    assert res2.session.row_version == 2
    assert res2.prompt == "Enter age:"

    # 3. Enter Invalid Age (Turn 2 - validation failure keeps state)
    res3 = session_service.execute("sess-100", "16")
    assert res3.session.current_state_id == "age_step"  # Unchanged
    assert res3.session.row_version == 3  # Version incremented on turn attempt
    assert "Value must be at least 18" in res3.prompt

    # 4. Enter Valid Age (Turn 3)
    res4 = session_service.execute("sess-100", "28")
    assert res4.session.current_state_id == "employed_step"
    assert res4.session.collected_data["age"] == 28

    # 5. Select Choice: Yes (Employed) -> Should branch to employer_step
    res5 = session_service.execute("sess-100", "1")
    assert res5.session.current_state_id == "employer_step"
    assert res5.session.collected_data["employed"] is True
    assert res5.prompt == "Enter employer name:"

    # 6. Enter Employer -> Reaches Terminal State
    res6 = session_service.execute("sess-100", "Stanbic Bank")
    assert res6.session.current_state_id == "complete_step"
    assert res6.session.status == "COMPLETED"
    assert res6.is_terminal is True
    assert res6.prompt == "Registration complete! Thank you."


def test_cannot_execute_turn_on_completed_session(
    session_service, branching_workflow
):
    """Verifies that SessionService blocks inputs to terminated sessions."""
    session_service.start(
        definition=branching_workflow,
        session_id="sess-200",
        version_id="wf-v1",
    )
    session_service.execute("sess-200", "Sarah")
    session_service.execute("sess-200", "28")
    session_service.execute(
        "sess-200", "2"
    )  # Selects 'No' -> Routes directly to complete_step

    # Session is now COMPLETED. Next execute should raise SessionTerminatedError
    with pytest.raises(SessionTerminatedError) as exc_info:
        session_service.execute("sess-200", "arbitrary_input")

    assert exc_info.value.session_id == "sess-200"
    assert exc_info.value.status == "COMPLETED"


def test_session_not_found_raises_error(session_service):
    """Verifies that querying a non-existent session raises SessionNotFoundError."""
    with pytest.raises(SessionNotFoundError):
        session_service.execute("non-existent-session-id", "test_input")


def test_optimistic_concurrency_conflict(session_service, branching_workflow):
    """Simulates two workers retrieving the same session version and colliding on save."""
    session_service.start(
        definition=branching_workflow,
        session_id="sess-300",
        version_id="wf-v1",
    )

    # Worker A and Worker B both load session (version = 1)
    session_worker_a = session_service.sessions.get("sess-300")
    session_worker_b = session_service.sessions.get("sess-300")
    assert (
        session_worker_a.row_version == session_worker_b.row_version == 1
    )

    # Worker A updates session successfully (version increments to 2)
    session_worker_a.collected_data["full_name"] = "Sarah"
    session_service.sessions.update(session_worker_a, expected_version=1)

    # Worker B attempts to update with stale expected_version=1 -> Fails!
    session_worker_b.collected_data["full_name"] = "Other Name"
    with pytest.raises(ConcurrencyConflictError) as exc_info:
        session_service.sessions.update(session_worker_b, expected_version=1)

    assert exc_info.value.expected_version == 1
    assert exc_info.value.actual_version == 2


def test_session_version_pinning(branching_workflow):
    """Verifies that an active session stays pinned to v1 even when a new version v2 is published."""
    workflow_repo = InMemoryWorkflowRepository()
    session_repo = InMemorySessionRepository()
    engine = WorkflowEngine()
    service = SessionService(engine, session_repo, workflow_repo)

    # 1. Register Version 1
    workflow_repo.save_version("wf-v1", branching_workflow)

    # 2. Register Version 2 (with a different prompt)
    v2_workflow = copy.deepcopy(branching_workflow)
    v2_workflow.states[0].prompt.default = "V2 PROMPT: What is your name?"
    workflow_repo.save_version("wf-v2", v2_workflow)

    # 3. Start Session pinned to wf-v1
    res1 = service.start(
        definition=branching_workflow,
        session_id="sess-pinned",
        version_id="wf-v1",
    )

    # Session prompt must be from v1, not v2
    assert res1.prompt == "Enter full name:"
    assert res1.session.workflow_version_id == "wf-v1"