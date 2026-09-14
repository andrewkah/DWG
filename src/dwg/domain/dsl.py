from typing import List, Literal, Optional, Union

from pydantic import BaseModel


class ConditionModel(BaseModel):
    field: str
    operator: Literal["equals", "not_equals", "gt", "gte", "lt", "lte", "in", "not_in", "equals"]
    value: Union[str, bool, int, float, List[Union[str, bool, float, int]]]
    
class TransitionModel(BaseModel):
    next: str
    condition: Optional[ConditionModel] = None
    
class PromptModel(BaseModel):
    default: str

class FieldValidationModel(BaseModel):
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min: Optional[int] = None
    max: Optional[int] = None
    pattern: Optional[str] = None
    
class ChoiceOptionModel(BaseModel):
    label: str
    value: Union[str, int, float, bool]
    

class FieldModel(BaseModel):
    name: str
    type: Literal["text", "integer", "decimal", "boolean", "choice"]
    required: bool
    sensitive: bool = False
    options: Optional[List[ChoiceOptionModel]] = None
    validation: Optional[FieldValidationModel] = None
    
class StateModel(BaseModel):
    id: str
    kind: Literal["input", "confirm", "terminal"]
    prompt: PromptModel
    field: Optional[FieldModel] = None
    transitions: Optional[List[TransitionModel]] = None
    terminal_status: Optional[Literal["COMPLETED", "CANCELLED"]] = None
    

class WorkflowDSLModel(BaseModel):
    dsl_schema_version: Literal["1.0"]
    workflow_id: str
    name: str
    description: Optional[str] = None
    start_state: str
    states: List[StateModel]
    
    def get_state(self, state_id: str) -> Optional[StateModel]:
        return next((s for s in self.states if s.id == state_id), None)