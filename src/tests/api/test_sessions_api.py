# tests/api/test_sessions_api.py
import pytest
from fastapi.testclient import TestClient

from dwg.api.schemas_and_dependencies import (
    get_session_repository,
    get_workflow_repository,
)
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
from dwg.main import create_app
from dwg.storage.redis_session import (
    InMemorySessionRepository,
    InMemoryWorkflowRepository,
)


@pytest.fixture
def sample_workflow() -> WorkflowDSLModel:
    return WorkflowDSLModel(
        dsl_schema_version="1.0",
        workflow_id="test_onboarding",
        name="Test Onboarding",
        start_state="name_step",
        states=[
            StateModel(
                id="name_step",
                kind="input",
                prompt=PromptModel(default="Enter full name:"),
                field=FieldModel(
                    name="name",
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
                    validation=FieldValidationModel(min=18, max=99),
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
                        condition=ConditionModel(field="employed", operator="equals", value=True),
                        next="employer_step",
                    ),
                    TransitionModel(
                        condition=ConditionModel(field="employed", operator="equals", value=False),
                        next="complete_step",
                    ),
                ],
            ),
            StateModel(
                id="employer_step",
                kind="input",
                prompt=PromptModel(default="Enter employer:"),
                field=FieldModel(name="employer", type="text", required=True),
                transitions=[TransitionModel(next="complete_step")],
            ),
            StateModel(
                id="complete_step",
                kind="terminal",
                terminal_status="COMPLETED",
                prompt=PromptModel(default="Registration complete!"),
            ),
        ],
    )


@pytest.fixture
def client(sample_workflow) -> TestClient:
    app = create_app()

    # Create fresh isolated repositories for each test run
    isolated_workflow_repo = InMemoryWorkflowRepository()
    isolated_session_repo = InMemorySessionRepository()

    # Pre-register test workflow
    isolated_workflow_repo.save_version("wf-v1", sample_workflow)

    # Override dependencies
    app.dependency_overrides[get_workflow_repository] = lambda: isolated_workflow_repo
    app.dependency_overrides[get_session_repository] = lambda: isolated_session_repo

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ==============================================================================
# TEST CASES
# ==============================================================================


def test_session_creation_success(client):
    """Assert successful session creation with HTTP 201 and initial state prompt."""
    response = client.post(
        "/api/v1/sessions",
        json={"workflow_version_id": "wf-v1", "session_id": "sess-01"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == "sess-01"
    assert data["workflow_version_id"] == "wf-v1"
    assert data["current_state_id"] == "name_step"
    assert data["status"] == "ACTIVE"
    assert data["prompt"] == "Enter full name:"
    assert data["is_terminal"] is False
    assert data["validation_error"] is None


def test_session_creation_unknown_version(client):
    """Assert 404 when workflow version does not exist."""
    response = client.post(
        "/api/v1/sessions",
        json={"workflow_version_id": "unknown-version"},
    )
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "WORKFLOW_VERSION_NOT_FOUND"


def test_successful_input_advances_state(client):
    """Assert valid turn moves the state machine forward and updates collected data."""
    client.post(
        "/api/v1/sessions",
        json={"workflow_version_id": "wf-v1", "session_id": "sess-02"},
    )

    step_res = client.post("/api/v1/sessions/sess-02/steps", json={"input": "Sarah Nabukeera"})
    assert step_res.status_code == 200
    data = step_res.json()
    assert data["current_state_id"] == "age_step"
    assert data["prompt"] == "Enter age:"
    assert data["collected_data"]["name"] == "Sarah Nabukeera"
    assert data["validation_error"] is None


def test_input_validation_failure_stays_on_current_state(client):
    """Assert invalid input returns 422, keeps current state, and provides error prompt."""
    client.post(
        "/api/v1/sessions",
        json={"workflow_version_id": "wf-v1", "session_id": "sess-03"},
    )
    client.post("/api/v1/sessions/sess-03/steps", json={"input": "Sarah Nabukeera"})

    # Submit invalid age (< 18)
    res = client.post("/api/v1/sessions/sess-03/steps", json={"input": "15"})
    assert res.status_code == 422
    data = res.json()
    assert data["current_state_id"] == "age_step"  # State did NOT advance
    assert "Value must be at least 18" in data["prompt"]
    assert data["validation_error"] == "Value must be at least 18."


def test_get_existing_session(client):
    """Assert retrieval of an active session snapshot."""
    client.post(
        "/api/v1/sessions",
        json={"workflow_version_id": "wf-v1", "session_id": "sess-04"},
    )

    res = client.get("/api/v1/sessions/sess-04")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == "sess-04"
    assert data["current_state_id"] == "name_step"
    assert data["prompt"] == "Enter full name:"


def test_get_unknown_session_returns_404(client):
    """Assert 404 when querying a non-existent session."""
    res = client.get("/api/v1/sessions/does-not-exist")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "SESSION_NOT_FOUND"


def test_submission_to_completed_session_returns_409(client):
    """Assert executing a turn on a completed session is rejected with HTTP 409 Conflict."""
    client.post(
        "/api/v1/sessions",
        json={"workflow_version_id": "wf-v1", "session_id": "sess-05"},
    )
    client.post("/api/v1/sessions/sess-05/steps", json={"input": "Sarah"})
    client.post("/api/v1/sessions/sess-05/steps", json={"input": "25"})
    # Select choice 2 (No) -> routes directly to terminal complete_step
    client.post("/api/v1/sessions/sess-05/steps", json={"input": "2"})

    # Session is now COMPLETED. Next turn attempt must fail
    res = client.post("/api/v1/sessions/sess-05/steps", json={"input": "Extra Input"})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "SESSION_ALREADY_TERMINATED"


def test_conditional_workflow_branching(client):
    """Assert choice input triggers ConditionModelal transition to the correct branch."""
    client.post(
        "/api/v1/sessions",
        json={"workflow_version_id": "wf-v1", "session_id": "sess-06"},
    )
    client.post("/api/v1/sessions/sess-06/steps", json={"input": "Sarah"})
    client.post("/api/v1/sessions/sess-06/steps", json={"input": "25"})

    # Select choice 1 (Yes) -> ConditionModel routes to employer_step
    res = client.post("/api/v1/sessions/sess-06/steps", json={"input": "1"})
    assert res.status_code == 200
    assert res.json()["current_state_id"] == "employer_step"
    assert res.json()["prompt"] == "Enter employer:"


def test_terminal_state_response(client):
    """Assert terminal state sets is_terminal=True and status=COMPLETED."""
    client.post(
        "/api/v1/sessions",
        json={"workflow_version_id": "wf-v1", "session_id": "sess-07"},
    )
    client.post("/api/v1/sessions/sess-07/steps", json={"input": "Sarah"})
    client.post("/api/v1/sessions/sess-07/steps", json={"input": "25"})
    # Select choice 2 (No) -> terminal complete_step
    res = client.post("/api/v1/sessions/sess-07/steps", json={"input": "2"})

    assert res.status_code == 200
    data = res.json()
    assert data["current_state_id"] == "complete_step"
    assert data["status"] == "COMPLETED"
    assert data["is_terminal"] is True
    assert data["prompt"] == "Registration complete!"


def test_malformed_request_body_returns_400(client):
    """Assert HTTP body validation failure returns 400 Bad Request."""
    # Missing required 'input' field in body
    res = client.post("/api/v1/sessions/sess-01/steps", json={})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "MALFORMED_REQUEST_BODY"


def test_dev_workflow_registration(client):
    """Assert dev-only endpoint registers workflow in memory for execution."""
    new_workflow = {
        "dsl_schema_version": "1.0",
        "workflow_id": "quick_poll",
        "name": "Quick Poll",
        "start_state": "done",
        "states": [
            {
                "id": "done",
                "kind": "terminal",
                "terminal_status": "COMPLETED",
                "prompt": {"default": "Thanks for voting!"},
            }
        ],
    }

    reg_res = client.post(
        "/api/v1/dev/workflows",
        json={"version_id": "poll-v1", "definition": new_workflow},
    )
    assert reg_res.status_code == 201

    # Now start a session on it
    start_res = client.post(
        "/api/v1/sessions",
        json={"workflow_version_id": "poll-v1", "session_id": "poll-01"},
    )
    assert start_res.status_code == 201
    assert start_res.json()["current_state_id"] == "done"
    assert start_res.json()["is_terminal"] is True
