from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


class ConditionModel(BaseModel):
    field: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    operator: Literal["equals", "not_equals", "gt", "gte", "lt", "lte", "in", "not_in", "exists"]
    value: Union[str, bool, int, float, List[Union[str, bool, float, int]]]
    
class TransitionModel(BaseModel):
    next: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    condition: Optional[ConditionModel] = None
    
class PromptModel(BaseModel):
    default: str = Field(..., min_length=1, max_length=320)

class FieldValidationModel(BaseModel):
    min_length: Optional[int] = Field(None, ge=1)
    max_length: Optional[int] = Field(None, ge=1)
    min: Optional[int] = None
    max: Optional[int] = None
    pattern: Optional[str] = None
    
class ChoiceOptionModel(BaseModel):
    label: str = Field(..., min_length=3, max_length=150)
    value: Union[str, int, float, bool]
    

class FieldModel(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    type: Literal["text", "integer", "decimal", "boolean", "choice"]
    required: bool
    sensitive: bool = False
    options: Optional[List[ChoiceOptionModel]] = Field(None, min_length=1)
    validation: Optional[FieldValidationModel] = None

    @model_validator(mode="after")
    def require_options_for_choice(self) -> "FieldModel":
        if self.type == "choice" and not self.options:
            raise ValueError("Choice fields require at least one option.")
        return self
    
class StateModel(BaseModel):
    id: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    kind: Literal["input", "confirm", "terminal"]
    prompt: PromptModel
    field: Optional[FieldModel] = None
    transitions: Optional[List[TransitionModel]] = None
    terminal_status: Optional[Literal["ACTIVE", "COMPLETED", "CANCELLED", "FAILED"]] = None
    

class WorkflowDSLModel(BaseModel):
    dsl_schema_version: Literal["1.0"]
    workflow_id: str = Field(..., pattern=r"^[a-z0-9_-]{3,64}$")
    name: str = Field(..., min_length=3, max_length=128)
    description: Optional[str] = Field(..., max_length=512)
    start_state: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    states: List[StateModel]
    
    def get_state(self, state_id: str) -> Optional[StateModel]:
        return next((s for s in self.states if s.id == state_id), f"State {state_id} not found in workflow definition!")