from typing import Any, Tuple

from dwg.domain.dsl import ConditionModel, FieldModel
from pydantic import field_validator, model_validator

class InputValidator:
    @staticmethod
    def validate_and_coerce(field_def: FieldModel, raw_input: Any) -> Tuple[bool, Any, str|None]:
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

        # 3. Type: CHOICE (Supports USSD indices and API direct values/labels)
        elif field_def.type == "choice":
            if not field_def.options:
                return False, None, "No options configured for this choice."

            val_str = str(raw_str).strip()

            # A. Check if input matches an option's value directly (or stringified value)
            for opt in field_def.options:
                if opt.value == raw_str or str(opt.value).lower() == val_str.lower():
                    return True, opt.value, None

            # B. Check if input matches an option's label case-insensitively
            for opt in field_def.options:
                if opt.label.lower() == val_str.lower():
                    return True, opt.value, None

            # C. Check if input is a 1-based numeric choice index (USSD style: "1", "2")
            if val_str.isdigit():
                try:
                    idx = int(val_str) - 1
                    if 0 <= idx < len(field_def.options):
                        return True, field_def.options[idx].value, None
                except ValueError:
                    pass

            # Build clear error message showing valid choices
            valid_choices = ", ".join([f"{i+1}. {opt.label}" for i, opt in enumerate(field_def.options)])
            return False, None, f"Invalid option selected. Please choose from: {valid_choices}"

        return True, raw_str, None
    
class ConditionEvaluator:
    """Validation model for workflow conditions."""
    
    @field_validator("operator")
    @staticmethod
    def validate_operator(op: str) -> str:
        if op not in ["equals", "not_equals", "gt", "gte", "lt", "lte", "in", "not_in", "exists"]:
                raise ValueError(f"Invalid conditiona operator: {op}.")
        return op
    
    @model_validator(mode="after")
    def evaluate_operator_and_value_fit(condition: ConditionModel, collected_data: dict[str, Any]) -> bool|str:
        """
        Evaluates a transition condition against accumulated session data.
        """
        field_val = collected_data.get(condition.field)
        op = condition.operator
        target_val = condition.value

        if op == "exists":
            return field_val is not None

        if field_val is None:
            return False

        # Normalize booleans vs string representations (e.g., True vs "true" / "1" / "yes")
        if isinstance(target_val, bool) and isinstance(field_val, str):
            field_val = field_val.strip().lower() in ("true", "1", "yes", "t", "y")
        elif isinstance(target_val, str) and isinstance(field_val, bool):
            target_val = target_val.strip().lower() in ("true", "1", "yes", "t", "y")

        # Evaluate supported operators
        if op == "equals":
            return field_val == target_val
        if op == "not_equals":
            return field_val != target_val
        if op == "gt":
            return field_val > target_val
        if op == "gte":
            return field_val >= target_val
        if op == "lt":
            return field_val < target_val
        if op == "lte":
            return field_val <= target_val
        if op == "in":
            return field_val in target_val
        if op == "not_in":
            return field_val not in target_val

        return False
            