from dwg.domain.dsl import ConditionModel, TransitionModel
import re
from pydantic import field_validator, model_validator

class ConditionValidator(ConditionModel):
    """Validation model for workflow conditions."""
    
    @field_validator("operator")
    @classmethod
    def validate_operator(cls, op: str) -> str:
        if op not in ["equals", "not_equals", "gt", "gte", "lt", "lte", "in", "not_in", "exists"]:
                raise ValueError(f"Invalid conditiona operator: {op}.")
        return op
    
    @model_validator(mode="after")
    def validate_operator_and_value_fit():
        condition_class = super()
        #   handle 'exists'
        if condition_class.operator == "exists":
            if condition_class.value is not None and not isinstance(condition_class.value, bool):
                raise ValueError("The 'exists' operator requires a boolean value!")
            return condition_class
        # Enforce a value for all other operators
        if condition_class.value is None:
            raise ValueError(f"Operator '{condition_class.operator}' requires a value.")

        # 3. Cross-field validation: 'in' and 'not_in' require an array (list)
        if condition_class.operator in ["in", "not_in"]:
            if not isinstance(condition_class.value, list):
                raise ValueError(f"Operator '{condition_class.operator}' requires an array of values.")
        
        # 4. Math operators should not be used on booleans or lists
        elif condition_class.operator in ["gt", "gte", "lt", "lte"]:
            if isinstance(condition_class.value, (list, bool)):
                raise ValueError(f"Operator '{condition_class.operator}' requires a number or string.")

        return condition_class
            