"""
Combines Rule Validator + Geocoding Analyzer + Pre-dispatch Check into a
single RecordValidationResult with a Green/Amber/Red rollup.

Rollup rule: any component RED -> record RED; else any component AMBER ->
record AMBER; else GREEN. This mirrors the SOW's traffic-light model where
RED is blocking, AMBER is a non-blocking concern needing review, and GREEN
is ready for the existing governed dispatch channel.
"""

from app.geocoding.mock_geocoder import analyze as analyze_geocoding
from app.maximo.predispatch import check as check_predispatch
from app.models.address_models import (
    BulkAddressCsvRow,
    RecordValidationResult,
    ValidationComponentResult,
    ValidationStatus,
)
from app.rules.validator import validate_record as validate_rules

_STATUS_RANK = {
    ValidationStatus.GREEN: 0,
    ValidationStatus.AMBER: 1,
    ValidationStatus.RED: 2,
}


def _rollup(components: list[ValidationComponentResult]) -> ValidationStatus:
    worst = ValidationStatus.GREEN
    for component in components:
        if _STATUS_RANK[component.status] > _STATUS_RANK[worst]:
            worst = component.status
    return worst


def validate_record(row: BulkAddressCsvRow) -> RecordValidationResult:
    rule_result = validate_rules(row)
    geocode_result = analyze_geocoding(row)
    predispatch_result = check_predispatch(row)

    final_status = _rollup([rule_result, geocode_result, predispatch_result])

    return RecordValidationResult(
        batchId=row.batchId,
        rowId=row.rowId,
        objectId=row.objectId,
        servicePointKey=row.servicePointKey,
        distributionSiteId=row.distributionSiteId,
        addressType=row.addressType,
        addressCombination=row.addressCombination,
        finalStatus=final_status,
        ruleValidation=rule_result,
        geocodeValidation=geocode_result,
        preDispatchValidation=predispatch_result,
    )
