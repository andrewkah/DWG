from typing import Any

from dwg.domain.dsl import ConditionModel, FieldModel
from pydantic import field_validator, model_validator

class InputValidator:
    @staticmethod
    def validate_and_coerce(field_def: FieldModel, raw_input: Any) -> Tuple(bool, Any, str|None):
        """Returns (is_valid, coerced_value, error_message)"""
        if raw_input is None or str(raw_input).strip() == "":
            if field_def.required:
                return False, None, "This field is required."
            return True, None, None

        raw_str = str(raw_input).strip()

        # 1. Type: INTEGER
        if field_def.type == "integer":
            try:
                val = int(raw_str)
            except ValueError:
                return (
                    False,
                    None,
                    "Invalid number. Please enter a valid whole number.",
                )

            if field_def.validation:
                if (
                    field_def.validation.min is not None
                    and val < field_def.validation.min
                ):
                    return (
                        False,
                        None,
                        f"Value must be at least {field_def.validation.min}.",
                    )
                if (
                    field_def.validation.max is not None
                    and val > field_def.validation.max
                ):
                    return (
                        False,
                        None,
                        f"Value must be at most {field_def.validation.max}.",
                    )
            return True, val, None

        # 2. Type: TEXT
        elif field_def.type == "text":
            if field_def.validation:
                if (
                    field_def.validation.min_length
                    and len(raw_str) < field_def.validation.min_length
                ):
                    return (
                        False,
                        None,
                        f"Must be at least {field_def.validation.min_length} characters.",
                    )
            return True, raw_str, None

        # 3. Type: CHOICE (e.g. 1 -> Yes, 2 -> No)
        elif field_def.type == "choice":
            # If user sent numeric choice index "1", "2"
            try:
                idx = int(raw_str) - 1
                if 0 <= idx < len(field_def.options):
                    return True, field_def.options[idx].value, None
            except ValueError:
                pass
            return False, None, "Invalid option selected. Please choose a valid number."

        return True, raw_str, None
    
class ConditionEvaluator(ConditionModel):
    """Validation model for workflow conditions."""
    
    @field_validator("operator")
    @staticmethod
    def validate_operator(op: str) -> str:
        if op not in ["equals", "not_equals", "gt", "gte", "lt", "lte", "in", "not_in", "exists"]:
                raise ValueError(f"Invalid conditiona operator: {op}.")
        return op
    
    @model_validator(mode="after")
    def evaluate_operator_and_value_fit(collected_data: dict[str, Any]) -> bool|str:
        condition_class = super()
        field_value = collected_data.get(condition_class.field)
        #   handle 'exists'
        if condition_class.operator == "exists":
            if condition_class.value is not None and not isinstance(condition_class.value, bool):
                raise ValueError("The 'exists' operator requires a boolean value!")
            return condition_class.field in collected_data
        # Enforce a value for all other operators
        elif field_value is None:
            raise ValueError(f"Operator '{condition_class.operator}' requires a value.")

        # 3. Cross-field validation: 'in' and 'not_in' require an array (list)
        elif condition_class.operator in ["in", "not_in"]:
            if not isinstance(field_value, list):
                raise ValueError(f"Operator '{condition_class.operator}' requires an array of values.")
            if condition_class.operator == "in":
                return field_value in condition_class.value
            if condition_class.operator == "not in":
                return field_value not in condition_class.value
        
        elif condition_class.operator == "gt":
            return field_value is not None and field_value > condition_class.value
        elif condition_class.operator == "gte":
            return field_value is not None and field_value >= condition_class.value
        elif condition_class.operator == "lt":
            return field_value is not None and field_value < condition_class.value
        elif condition_class.operator == "lte":
            return field_value is not None and field_value <= condition_class.value

        return False
            