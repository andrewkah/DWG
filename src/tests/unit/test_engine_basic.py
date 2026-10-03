
from dwg.domain.dsl import FieldModel, FieldValidationModel, PromptModel, StateModel, TransitionModel, WorkflowDSLModel
from dwg.engine.state_machine import WorkflowEngine


def build_sample_workflow() -> WorkflowDSLModel:
    return WorkflowDSLModel(dsl_schema_version = "1.0", workflow_id="onboarding", name="User Onboarding", description="User Onboarding workflow testing...", start_state="full_name", 
                            states=[
                                StateModel(
                                    id="full_name", kind="input", prompt=PromptModel(default="Enter your full name:"),
                                    field=FieldModel(name="full_name", type="text", required=True, sensitive=True, validation=FieldValidationModel(min_length=3, max_length=255)),
                                    transitions=[TransitionModel(next="age")]
                                ),
                                StateModel(
                                    id="age", kind="input", prompt=PromptModel(default="Enter your age:"),
                                    field=FieldModel(name="age", type="integer", required=True, validation=FieldValidationModel(min=16)),
                                    transitions=[TransitionModel(next="done")]
                                ),
                                StateModel(
                                    id="done",
                                    kind="terminal",
                                    prompt=PromptModel(default="Thank you! Registration complete."),
                                )
                            ]
                        )

def test_linear_worklflow_progression():
    engine = WorkflowEngine()
    workflow = build_sample_workflow()
    # Start workflow
    first_res = engine.start_session(workflow, session_id="session_1", version_id="v1")
    assert first_res.session.current_state_id == "full_name"
    assert first_res.prompt == "Enter your full name:"
    assert not first_res.is_terminal
    # Submit invalid name (too short)
    first_res2 = engine.execute_turn(workflow, first_res.session, input="J")
    assert first_res2.session.current_state_id == "full_name" # Did not advance to next step
    assert "Must be at least 3 characters" in first_res2.prompt
    # Submit Valid full name
    second_res = engine.execute_turn(workflow, first_res2.session, input="Jackson")
    assert second_res.session.current_state_id == "age"  # Advanced to next step
    assert second_res.prompt == "Enter your age:"
    assert second_res.session.collected_data["full_name"] == "Jackson"
    # Submit invalid age (< 18)
    res4 = engine.execute_turn(workflow, second_res.session, input="15")
    assert res4.session.current_state_id == "age"  # Did not advance!
    assert "Value must be at least 16" in res4.prompt

    # Step 5: Submit valid age
    res5 = engine.execute_turn(workflow, res4.session, input="25")
    assert res5.session.current_state_id == "done"
    assert res5.session.status == "COMPLETED"
    assert res5.is_terminal
    assert res5.session.collected_data["age"] == 25
    assert res5.prompt == "Thank you! Registration complete."
    