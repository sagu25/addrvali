"""
Capability 5: Batch Analysis.

Runs record-level validation across every row of an uploaded batch and
rolls the results up into a BulkAddressValidationResponse.
"""

import uuid

from app.ai.explanations import explain_record
from app.models.address_models import (
    BulkAddressCsvRow,
    BulkAddressValidationResponse,
    ValidationStatus,
)
from app.orchestration import batch_store
from app.orchestration.record_validator import validate_record


def validate_batch(
    rows: list[BulkAddressCsvRow], batch_id: str | None = None
) -> BulkAddressValidationResponse:
    resolved_batch_id = batch_id or str(uuid.uuid4())

    results = []
    for row in rows:
        row.batchId = row.batchId or resolved_batch_id
        record_result = validate_record(row)
        record_result = explain_record(record_result)
        results.append(record_result)

    green_count = sum(1 for r in results if r.finalStatus == ValidationStatus.GREEN)
    amber_count = sum(1 for r in results if r.finalStatus == ValidationStatus.AMBER)
    red_count = sum(1 for r in results if r.finalStatus == ValidationStatus.RED)

    response = BulkAddressValidationResponse(
        batchId=resolved_batch_id,
        totalRecords=len(results),
        greenCount=green_count,
        amberCount=amber_count,
        redCount=red_count,
        results=results,
    )

    batch_store.save_batch(resolved_batch_id, rows, response)
    return response
