import pytest
from fastapi.testclient import TestClient
from dwg.api.schemas_and_dependencies import (
    get_session_repository,
    get_workflow_repository,
)
from dwg.api.v1.ussd import get_ussd_channel_service
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
from dwg.engine.services.session_service import SessionService
from dwg.adapters.ussd.ussd_service import UssdChannelService
from dwg.storage.redis_session import (
    InMemorySessionRepository,
    InMemoryWorkflowRepository,
)


@pytest.fixture
def kyc_workflow() -> WorkflowDSLModel:
    return WorkflowDSLModel(
        dsl_schema_version="1.0",
        workflow_id="ussd_kyc",
        name="USSD KYC",
        start_state="name_step",
        states=[
            StateModel(
                id="name_step",
                kind="input",
                prompt=PromptModel(default="Welcome. Enter full name:"),
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
                    validation=FieldValidationModel(min=18),
                ),
                transitions=[TransitionModel(next="employed_step")],
            ),
            StateModel(
                id="employed_step",
                kind="input",
                prompt=PromptModel(default="Employed?\n1. Yes\n2. No"),
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
                        next="done_step",
                    ),
                ],
            ),
            StateModel(
                id="employer_step",
                kind="input",
                prompt=PromptModel(default="Enter employer:"),
                field=FieldModel(
                    name="employer", type="text", required=True
                ),
                transitions=[TransitionModel(next="done_step")],
            ),
            StateModel(
                id="done_step",
                kind="terminal",
                terminal_status="COMPLETED",
                prompt=PromptModel(default="Thank you! Registration complete."),
            ),
        ],
    )


@pytest.fixture
def client(kyc_workflow) -> TestClient: # type: ignore
    app = create_app()

    isolated_wf_repo = InMemoryWorkflowRepository()
    isolated_sess_repo = InMemorySessionRepository()

    # Pre-register workflow definition
    isolated_wf_repo.save_version("kyc-v1", kyc_workflow)

    # Setup isolated SessionService and UssdChannelService
    from dwg.engine.state_machine import WorkflowEngine

    engine = WorkflowEngine()
    session_service = SessionService(
        engine, isolated_sess_repo, isolated_wf_repo
    )
    ussd_service = UssdChannelService(session_service, isolated_wf_repo)

    # Bind short code *384*100# to kyc-v1
    ussd_service.bind_shortcode("*384*100#", "kyc-v1")

    # Dependency overrides
    app.dependency_overrides[get_workflow_repository] = lambda: isolated_wf_repo
    app.dependency_overrides[get_session_repository] = lambda: isolated_sess_repo
    app.dependency_overrides[get_ussd_channel_service] = lambda: ussd_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ==============================================================================
# TESTS
# ==============================================================================


def test_mock_provider_full_flow(client):
    """Verifies a multi-turn interactive session using the Mock provider."""
    sess_id = "test-sess-001"

    # Turn 1: Dial-in
    r1 = client.post(
        "/api/v1/ussd/mock",
        data={
            "session_id": sess_id,
            "service_code": "*384*100#",
            "phone_number": "+256770123456",
            "text": "",
            "is_new": True,
        },
    )
    assert r1.status_code == 200
    assert r1.text == "CON Welcome. Enter full name:"

    # Turn 2: Enter Name
    r2 = client.post(
        "/api/v1/ussd/mock",
        data={
            "session_id": sess_id,
            "service_code": "*384*100#",
            "phone_number": "+256770123456",
            "text": "Andrew Mugisha",
            "is_new": False,
        },
    )
    assert r2.status_code == 200
    assert r2.text == "CON Enter age:"

    # Turn 3: Enter Invalid Age (< 18) -> Must stay on age_step with re-prompt
    r3 = client.post(
        "/api/v1/ussd/mock",
        data={
            "session_id": sess_id,
            "service_code": "*384*100#",
            "phone_number": "+256770123456",
            "text": "16",
            "is_new": False,
        },
    )
    assert r3.status_code == 200
    assert r3.text.startswith("CON Value must be at least 18")

    # Turn 4: Enter Valid Age (25)
    r4 = client.post(
        "/api/v1/ussd/mock",
        data={
            "session_id": sess_id,
            "service_code": "*384*100#",
            "phone_number": "+256770123456",
            "text": "25",
            "is_new": False,
        },
    )
    assert r4.status_code == 200
    assert r4.text == "CON Employed?\n1. Yes\n2. No"

    # Turn 5: Select 2 (No) -> Branches straight to done_step
    r5 = client.post(
        "/api/v1/ussd/mock",
        data={
            "session_id": sess_id,
            "service_code": "*384*100#",
            "phone_number": "+256770123456",
            "text": "2",
            "is_new": False,
        },
    )
    assert r5.status_code == 200
    assert r5.text == "END Thank you! Registration complete."


def test_africas_talking_turn_concatenation(client):
    """Verifies that Africa's Talking asterisk (*) concatenation is parsed accurately."""
    sess_id = "AT_Sess_998877"

    # Turn 1: Dial-in (text is empty)
    r1 = client.post(
        "/api/v1/ussd/africas_talking",
        data={
            "sessionId": sess_id,
            "phoneNumber": "+256770123456",
            "serviceCode": "*384*100#",
            "text": "",
        },
    )
    assert r1.status_code == 200
    assert r1.text == "CON Welcome. Enter full name:"

    # Turn 2: Africa's Talking sends text="Sarah Nabukeera"
    r2 = client.post(
        "/api/v1/ussd/africas_talking",
        data={
            "sessionId": sess_id,
            "phoneNumber": "+256770123456",
            "serviceCode": "*384*100#",
            "text": "Sarah Nabukeera",
        },
    )
    assert r2.status_code == 200
    assert r2.text == "CON Enter age:"

    # Turn 3: Africa's Talking sends text="Sarah Nabukeera*28"
    r3 = client.post(
        "/api/v1/ussd/africas_talking",
        data={
            "sessionId": sess_id,
            "phoneNumber": "+256770123456",
            "serviceCode": "*384*100#",
            "text": "Sarah Nabukeera*28",
        },
    )
    assert r3.status_code == 200
    assert r3.text == "CON Employed?\n1. Yes\n2. No"

    # Turn 4: Africa's Talking sends text="Sarah Nabukeera*28*1" (Employed = Yes)
    r4 = client.post(
        "/api/v1/ussd/africas_talking",
        data={
            "sessionId": sess_id,
            "phoneNumber": "+256770123456",
            "serviceCode": "*384*100#",
            "text": "Sarah Nabukeera*28*1",
        },
    )
    assert r4.status_code == 200
    assert r4.text == "CON Enter employer:"

    # Turn 5: Africa's Talking sends text="Sarah Nabukeera*28*1*Stanbic" -> Terminal
    r5 = client.post(
        "/api/v1/ussd/africas_talking",
        data={
            "sessionId": sess_id,
            "phoneNumber": "+256770123456",
            "serviceCode": "*384*100#",
            "text": "Sarah Nabukeera*28*1*Stanbic",
        },
    )
    assert r5.status_code == 200
    assert r5.text == "END Thank you! Registration complete."


def test_unbound_shortcode_returns_end(client):
    """Verifies that dialing an unconfigured short code returns a clean terminal END message."""
    res = client.post(
        "/api/v1/ussd/mock",
        data={
            "session_id": "unbound-sess",
            "service_code": "*999#",  # Not bound
            "phone_number": "+256700000000",
            "text": "",
            "is_new": True,
        },
    )
    assert res.status_code == 200
    assert res.text.startswith("END Service code not configured")


def test_unsupported_provider_returns_404(client):
    """Verifies that querying an unrecognized provider slug returns HTTP 404."""
    res = client.post("/api/v1/ussd/unknown_telco", data={})
    assert res.status_code == 404