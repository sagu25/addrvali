import os

from app.ai.chat_agent import handle_message
from app.ai.tools import get_record, list_records, recheck_record
from app.ingestion.excel_parser import parse_workbook
from app.orchestration.batch_validator import validate_batch

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_mixed_batch():
    with open(os.path.join(FIXTURES_DIR, "mixed_batch.xlsx"), "rb") as f:
        parsed = parse_workbook(f.read())
    return validate_batch(parsed.rows, batch_id="test-batch-mixed")


def test_get_record_returns_stored_result():
    batch = _load_mixed_batch()
    result = get_record(batch.batchId, 2)
    assert result["finalStatus"] == "RED"
    assert result["rowId"] == 2


def test_get_record_unknown_row_returns_error():
    batch = _load_mixed_batch()
    result = get_record(batch.batchId, 999)
    assert "error" in result


def test_recheck_record_fixes_missing_street_name():
    batch = _load_mixed_batch()
    # Row 2 is RED because streetName is missing for UrbanStreet.
    original = get_record(batch.batchId, 2)
    assert original["finalStatus"] == "RED"

    result = recheck_record(batch.batchId, 2, {"streetName": "Fixed Avenue"})
    assert "error" not in result
    assert result["appliedUpdates"] == {"streetName": "Fixed Avenue"}
    # rule error about streetName should be gone now
    rule_errors = [e["fieldName"] for e in result["ruleValidation"]["errors"]]
    assert "streetName" not in rule_errors


def test_recheck_record_does_not_mutate_stored_batch():
    batch = _load_mixed_batch()
    recheck_record(batch.batchId, 2, {"streetName": "Fixed Avenue"})
    # stored original should be unchanged
    still_original = get_record(batch.batchId, 2)
    assert still_original["finalStatus"] == "RED"


def test_recheck_record_unresolvable_field():
    batch = _load_mixed_batch()
    result = recheck_record(batch.batchId, 2, {"not_a_real_field_xyz": "value"})
    assert "error" in result


def test_list_records_filters_by_status():
    batch = _load_mixed_batch()
    red = list_records(batch.batchId, "RED")
    assert red["count"] == 5
    green = list_records(batch.batchId, "GREEN")
    assert green["count"] == 3


def test_fallback_row_lookup():
    batch = _load_mixed_batch()
    response = handle_message(batch.batchId, "why is row 2 red?")
    assert "row 2" in response["reply"].lower() or "streetname" in response["reply"].lower()


def test_fallback_what_if():
    batch = _load_mixed_batch()
    response = handle_message(batch.batchId, "row 2 streetName=Fixed Avenue")
    assert response["updatedRecord"] is not None
    assert response["updatedRecord"]["finalStatus"] == "GREEN"


def test_fallback_status_list():
    batch = _load_mixed_batch()
    response = handle_message(batch.batchId, "which rows are red?")
    assert "Row 2" in response["reply"] or "row 2" in response["reply"].lower()


def test_unknown_batch_id_returns_friendly_message():
    response = handle_message("does-not-exist", "row 1")
    assert "upload" in response["reply"].lower()
