from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field


class ConditionModel(BaseModel):
    field: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    operator: Literal["equals", "not_equals", "gt", "gte", "lt", "lte", "in", "not_in", "equals"]
    value: Union[str, bool, int, float, List[Union[str, bool, float, int]]]
    
class TransitionModel(BaseModel):
    next: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    condition: Optional[ConditionModel] = None
    
class PromptModel(BaseModel):
    default: str = Field(..., min_length=1, max_length=320)

class FieldValidationModel(BaseModel):
    min_length: Optional[int] = Field(..., ge=1)
    max_length: Optional[int] = Field(..., ge=1)
    min: Optional[int] = None
    max: Optional[int] = None
    pattern: Optional[str] = None
    
class ChoiceOptionModel(BaseModel):
    label: str = Field(..., min_length=1, max_length=64)
    value: Union[str, int, float, bool]
    

class FieldModel(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    type: Literal["text", "integer", "decimal", "boolean", "choice"]
    required: bool
    sensitive: bool = False
    options: Optional[List[ChoiceOptionModel]] = Field(..., min_items=1,)
    validation: Optional[FieldValidationModel] = None
    
class StateModel(BaseModel):
    id: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    kind: Literal["input", "confirm", "terminal"]
    prompt: PromptModel
    field: Optional[FieldModel] = None
    transitions: Optional[List[TransitionModel]] = None
    terminal_status: Optional[Literal["COMPLETED", "CANCELLED"]] = None
    

class WorkflowDSLModel(BaseModel):
    dsl_schema_version: Literal["1.0"]
    workflow_id: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    name: str = Field(..., min_length=3, max_length=128)
    description: Optional[str] = Field(..., max_length=512)
    start_state: str = Field(..., pattern=r"^[a-z0-9_]{1,64}$")
    states: List[StateModel]
    
    def get_state(self, state_id: str) -> Optional[StateModel]:
        return next((s for s in self.states if s.id == state_id), None)