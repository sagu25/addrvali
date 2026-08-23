"""
Tools the chat agent can call to answer follow-up questions about an
already-validated batch. Each tool is read-only or purely simulated -
recheck_record never writes back to the stored batch, matching the
"explains, never decides" boundary from the SOW.
"""

from app.ai.explanations import explain_record
from app.ingestion.excel_parser import HEADER_ALIASES
from app.models.address_models import BulkAddressCsvRow
from app.orchestration import batch_store
from app.orchestration.record_validator import validate_record

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_record",
            "description": (
                "Get the full validation result (status, rule/geocode/Maximo "
                "errors and warnings, explanation) for one row in the current "
                "batch by its row number."
            ),
            "parameters": {
                "type": "object",
                "properties": {"rowId": {"type": "integer"}},
                "required": ["rowId"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recheck_record",
            "description": (
                "Simulate changing one or more fields on a row and re-run the "
                "full validation pipeline (rules, geocoding, Maximo readiness) "
                "against the hypothetical values. Does NOT save or apply the "
                "change to the real record - it is a what-if check only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "rowId": {"type": "integer"},
                    "fieldUpdates": {
                        "type": "object",
                        "description": (
                            "Map of field name (e.g. postalCode, streetName, "
                            "distributionSiteId) to new string value."
                        ),
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": ["rowId", "fieldUpdates"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_records",
            "description": "List rows in the current batch, optionally filtered by status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["GREEN", "AMBER", "RED"],
                    }
                },
            },
        },
    },
]


def resolve_field_name(text: str) -> str | None:
    """Map a loosely-typed field reference ('postal code', 'Street Name') to
    a real BulkAddressCsvRow field name, reusing the same alias table the
    Excel ingestion uses so 'the field means the same thing everywhere'."""
    key = text.strip().lower()
    if key in HEADER_ALIASES:
        return HEADER_ALIASES[key]
    for field_name in BulkAddressCsvRow.model_fields:
        if field_name.lower() == key:
            return field_name
    return None


def get_record(batch_id: str, row_id: int) -> dict:
    record = batch_store.get_record_result(batch_id, row_id)
    if record is None:
        return {"error": f"No row {row_id} found in this batch."}
    return record.model_dump(mode="json")


def recheck_record(batch_id: str, row_id: int, field_updates: dict) -> dict:
    original_row = batch_store.get_row(batch_id, row_id)
    if original_row is None:
        return {"error": f"No row {row_id} found in this batch."}

    resolved_updates = {}
    unknown_fields = []
    for raw_field, value in field_updates.items():
        resolved = resolve_field_name(raw_field) or (
            raw_field if raw_field in BulkAddressCsvRow.model_fields else None
        )
        if resolved is None:
            unknown_fields.append(raw_field)
        else:
            resolved_updates[resolved] = value

    if not resolved_updates:
        return {
            "error": "None of the given fields are recognised address fields.",
            "unknownFields": unknown_fields,
        }

    merged = original_row.model_dump(mode="json")
    merged.update(resolved_updates)
    try:
        hypothetical_row = BulkAddressCsvRow(**merged)
    except Exception as exc:
        return {"error": f"That change produces an invalid record: {exc}"}

    result = validate_record(hypothetical_row)
    result = explain_record(result)
    payload = result.model_dump(mode="json")
    payload["appliedUpdates"] = resolved_updates
    if unknown_fields:
        payload["ignoredFields"] = unknown_fields
    payload["note"] = "This is a what-if simulation only - nothing was saved."
    return payload


def list_records(batch_id: str, status: str | None = None) -> dict:
    batch = batch_store.get_batch(batch_id)
    if batch is None:
        return {"error": "Unknown batch."}
    records = batch.response.results
    if status:
        records = [r for r in records if r.finalStatus.value == status]
    return {
        "count": len(records),
        "rows": [
            {
                "rowId": r.rowId,
                "status": r.finalStatus.value,
                "servicePointKey": r.servicePointKey,
                "addressCombination": r.addressCombination.value if r.addressCombination else None,
            }
            for r in records
        ],
    }


DISPATCH = {
    "get_record": lambda batch_id, args: get_record(batch_id, args["rowId"]),
    "recheck_record": lambda batch_id, args: recheck_record(
        batch_id, args["rowId"], args.get("fieldUpdates", {})
    ),
    "list_records": lambda batch_id, args: list_records(batch_id, args.get("status")),
}


def call_tool(name: str, batch_id: str, arguments: dict) -> dict:
    handler = DISPATCH.get(name)
    if handler is None:
        return {"error": f"Unknown tool '{name}'."}
    return handler(batch_id, arguments)
