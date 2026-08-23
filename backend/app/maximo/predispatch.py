"""
Capability 3: Pre-dispatch Check - MOCKED for the POC.

Simulates whether the proposed record would build a valid Maximo payload,
without actually calling the real Maximo REST channel. Uses a small
synthetic "required linking fields" schema rather than ATCO's real Maximo
contract - swap for the real schema/endpoint once the Maximo dependency is
confirmed.

Synthetic test data can force a schema conflict by putting the token
MAXCONFLICT anywhere in servicePointKey or distributionSiteId.
"""

from app.models.address_models import (
    BulkAddressCsvRow,
    ValidationComponentResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationStatus,
)

COMPONENT_NAME = "PreDispatchCheck"

# Synthetic Maximo linking-field schema: fields the mock payload build
# considers mandatory before a record could ever reach Maximo.
REQUIRED_LINKING_FIELDS = [
    "servicePointKey",
    "distributionSiteId",
    "objectId",
    "changedBy",
]


def _is_populated(value) -> bool:
    return value not in (None, "")


def check(row: BulkAddressCsvRow) -> ValidationComponentResult:
    row_values = row.model_dump()
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    metadata: dict = {}

    missing_fields = [
        field_name
        for field_name in REQUIRED_LINKING_FIELDS
        if not _is_populated(row_values.get(field_name))
    ]
    for field_name in missing_fields:
        errors.append(
            ValidationIssue(
                fieldName=field_name,
                message=f"Maximo payload is missing required linking field '{field_name}'.",
                severity=ValidationSeverity.ERROR,
            )
        )

    conflict_flag = any(
        "MAXCONFLICT" in str(row_values.get(field_name, "")).upper()
        for field_name in ("servicePointKey", "distributionSiteId")
    )
    if conflict_flag:
        errors.append(
            ValidationIssue(
                fieldName="servicePointKey",
                message="Simulated Maximo payload conflicts with an existing record schema.",
                severity=ValidationSeverity.ERROR,
            )
        )

    metadata["missingFields"] = missing_fields
    metadata["payloadReady"] = not errors

    status = ValidationStatus.RED if errors else ValidationStatus.GREEN

    return ValidationComponentResult(
        componentName=COMPONENT_NAME,
        status=status,
        errors=errors,
        warnings=warnings,
        metadata=metadata,
    )
