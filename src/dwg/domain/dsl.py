from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ConditionModel(BaseModel):
    field: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    operator: Literal[
        "equals", "not_equals", "gt", "gte", "lt", "lte", "in", "not_in", "exists"
    ]
    value: str | bool | int | float | list[str | bool | float | int]


class TransitionModel(BaseModel):
    next: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    condition: ConditionModel | None = None


class PromptModel(BaseModel):
    default: str = Field(..., min_length=1, max_length=320)


class FieldValidationModel(BaseModel):
    min_length: int | None = Field(None, ge=1)
    max_length: int | None = Field(None, ge=1)
    min: int | None = None
    max: int | None = None
    pattern: str | None = None


class ChoiceOptionModel(BaseModel):
    label: str = Field(..., min_length=2, max_length=150)
    value: str | int | float | bool


class FieldModel(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    type: Literal["text", "integer", "decimal", "boolean", "choice"]
    required: bool
    sensitive: bool = False
    options: list[ChoiceOptionModel] | None = Field(None, min_length=1)
    validation: FieldValidationModel | None = None

    @model_validator(mode="after")
    def require_options_for_choice(self) -> "FieldModel":
        if self.type == "choice" and not self.options:
            raise ValueError("Choice fields require at least one option.")
        return self


class StateModel(BaseModel):
    id: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    kind: Literal["input", "confirm", "terminal"]
    prompt: PromptModel
    field: FieldModel | None = None
    transitions: list[TransitionModel] | None = None
    terminal_status: Literal["ACTIVE", "COMPLETED", "CANCELLED", "FAILED"] | None = None


class WorkflowDSLModel(BaseModel):
    dsl_schema_version: Literal["1.0"]
    workflow_id: str = Field(..., pattern=r"^[a-z0-9_-]{3,64}$")
    name: str = Field(..., min_length=3, max_length=128)
    description: str | None = Field(None, max_length=512)
    start_state: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    states: list[StateModel]

    def get_state(self, state_id: str) -> StateModel | None:
        return next(
            (s for s in self.states if s.id == state_id),
            f"State {state_id} not found in workflow definition!",
        )
