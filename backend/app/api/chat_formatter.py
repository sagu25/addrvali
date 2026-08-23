"""
Turns a BulkAddressValidationResponse into a single conversational chat
message, so the React chat window can render one bot bubble instead of a
raw table. The structured response is still returned alongside it for the
UI to build an expandable per-record detail view.
"""

from app.models.address_models import (
    BulkAddressValidationResponse,
    RecordValidationResult,
    ValidationStatus,
)

_STATUS_EMOJI = {
    ValidationStatus.GREEN: "🟢",
    ValidationStatus.AMBER: "🟠",
    ValidationStatus.RED: "🔴",
}


def _first_issue_message(record: RecordValidationResult) -> str | None:
    for component in (
        record.ruleValidation,
        record.geocodeValidation,
        record.preDispatchValidation,
    ):
        if component is None:
            continue
        if component.errors:
            return component.errors[0].message
        if component.warnings:
            return component.warnings[0].message
    return None


def format_chat_message(batch: BulkAddressValidationResponse, parse_errors: list[dict]) -> str:
    lines = [
        f"Processed **{batch.totalRecords}** record(s) from this upload:",
        f"🟢 {batch.greenCount} ready   🟠 {batch.amberCount} needs review   🔴 {batch.redCount} blocked",
    ]

    if parse_errors:
        lines.append("")
        lines.append(f"⚠️ {len(parse_errors)} row(s) could not be parsed and were skipped:")
        for err in parse_errors[:10]:
            lines.append(f"  - Row {err['rowId']}: {err['error']}")
        if len(parse_errors) > 10:
            lines.append(f"  - ...and {len(parse_errors) - 10} more.")

    non_green = [r for r in batch.results if r.finalStatus != ValidationStatus.GREEN]
    if non_green:
        lines.append("")
        lines.append("Records needing attention:")
        for record in non_green[:20]:
            emoji = _STATUS_EMOJI[record.finalStatus]
            label = f"Row {record.rowId}" if record.rowId is not None else "Record"
            reason = _first_issue_message(record) or "See details below."
            lines.append(f"  {emoji} {label}: {reason}")
        if len(non_green) > 20:
            lines.append(f"  ...and {len(non_green) - 20} more - see full details below.")
    else:
        lines.append("")
        lines.append("All records passed. Nothing further needed before dispatch.")

    return "\n".join(lines)
