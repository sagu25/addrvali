"""
Capability 1: Rule Validator.

Checks a BulkAddressCsvRow's populated fields against the ATCO rule matrix
for its declared AddressCombination. Fully deterministic - no LLM, no
network calls.
"""

from app.models.address_models import (
    BulkAddressCsvRow,
    ValidationComponentResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationStatus,
)
from app.rules.matrix import FIELD_ORDER, RULE_MATRIX, FieldRule

COMPONENT_NAME = "RuleValidator"


def _is_populated(value) -> bool:
    return value not in (None, "")


def validate_record(row: BulkAddressCsvRow) -> ValidationComponentResult:
    if row.addressCombination is None:
        return ValidationComponentResult(
            componentName=COMPONENT_NAME,
            status=ValidationStatus.RED,
            errors=[
                ValidationIssue(
                    fieldName="addressCombination",
                    message="addressCombination is required to select a rule set.",
                    severity=ValidationSeverity.ERROR,
                )
            ],
        )

    combination_key = row.addressCombination.name
    field_rules = RULE_MATRIX.get(combination_key)
    if field_rules is None:
        return ValidationComponentResult(
            componentName=COMPONENT_NAME,
            status=ValidationStatus.RED,
            errors=[
                ValidationIssue(
                    fieldName="addressCombination",
                    message=f"No rule set defined for combination '{combination_key}'.",
                    severity=ValidationSeverity.ERROR,
                )
            ],
        )

    row_values = row.model_dump()
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    for field_name in FIELD_ORDER:
        rule = field_rules.get(field_name, FieldRule.NA)
        populated = _is_populated(row_values.get(field_name))

        if rule == FieldRule.REQUIRED and not populated:
            errors.append(
                ValidationIssue(
                    fieldName=field_name,
                    message=(
                        f"'{field_name}' is required for combination "
                        f"'{combination_key}' but was not provided."
                    ),
                    severity=ValidationSeverity.ERROR,
                )
            )
        elif rule in (FieldRule.NOT_ALLOWED, FieldRule.NA) and populated:
            errors.append(
                ValidationIssue(
                    fieldName=field_name,
                    message=(
                        f"'{field_name}' is not allowed for combination "
                        f"'{combination_key}' but a value was provided."
                    ),
                    severity=ValidationSeverity.ERROR,
                )
            )
        # OPTIONAL: no action needed whether populated or not.

    if errors:
        status = ValidationStatus.RED
    elif warnings:
        status = ValidationStatus.AMBER
    else:
        status = ValidationStatus.GREEN

    return ValidationComponentResult(
        componentName=COMPONENT_NAME,
        status=status,
        errors=errors,
        warnings=warnings,
        metadata={"combination": combination_key},
    )
