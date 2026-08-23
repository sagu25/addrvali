"""
In-memory store of validated batches, keyed by batchId.

Lets the chat agent answer follow-up questions ("why is row 3 red?",
"what if I fix the postal code?") without the user re-uploading the
workbook. POC-scoped: single process, no persistence, no eviction. A real
deployment would back this with a session store or short-TTL cache.
"""

from dataclasses import dataclass

from app.models.address_models import BulkAddressCsvRow, BulkAddressValidationResponse

_STORE: dict[str, "StoredBatch"] = {}


@dataclass
class StoredBatch:
    rows_by_id: dict[int, BulkAddressCsvRow]
    response: BulkAddressValidationResponse


def save_batch(batch_id: str, rows: list[BulkAddressCsvRow], response: BulkAddressValidationResponse) -> None:
    rows_by_id = {row.rowId: row for row in rows if row.rowId is not None}
    _STORE[batch_id] = StoredBatch(rows_by_id=rows_by_id, response=response)


def get_batch(batch_id: str) -> StoredBatch | None:
    return _STORE.get(batch_id)


def get_row(batch_id: str, row_id: int) -> BulkAddressCsvRow | None:
    batch = _STORE.get(batch_id)
    if batch is None:
        return None
    return batch.rows_by_id.get(row_id)


def get_record_result(batch_id: str, row_id: int):
    batch = _STORE.get(batch_id)
    if batch is None:
        return None
    for record in batch.response.results:
        if record.rowId == row_id:
            return record
    return None
