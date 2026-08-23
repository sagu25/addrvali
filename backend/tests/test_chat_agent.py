import json
import os

import app.ai.chat_agent as chat_agent
from app.ai.chat_agent import handle_message
from app.ai.tools import get_record, list_records, recheck_record
from app.config import settings
from app.ingestion.excel_parser import parse_workbook
from app.orchestration.batch_validator import validate_batch

from tests.fake_azure import FakeAzureClient, FakeMessage, FakeResponse, FakeToolCall, configure_fake_azure

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


def test_unknown_batch_id_returns_friendly_message():
    response = handle_message("does-not-exist", "row 1")
    assert "upload" in response["reply"].lower()
    assert response["source"] == "no_batch"


def test_without_azure_configured_returns_explicit_not_configured_message():
    # No AZURE_OPENAI_* env vars set in the test environment - there is no
    # fallback parser anymore, so this must say so plainly, not guess an answer.
    batch = _load_mixed_batch()
    response = handle_message(batch.batchId, "why is row 2 red?")
    assert response["source"] == "not_configured"
    assert "not configured" in response["reply"].lower()


def test_llm_handle_answers_using_tool_call_then_final_message(monkeypatch):
    batch = _load_mixed_batch()
    configure_fake_azure(monkeypatch, settings)

    tool_call = FakeToolCall("call_1", "get_record", json.dumps({"rowId": 2}))
    first_response = FakeResponse(FakeMessage(content=None, tool_calls=[tool_call]))
    final_response = FakeResponse(FakeMessage(content="Row 2 is red because streetName is missing.", tool_calls=None))
    fake_client = FakeAzureClient(responses=[first_response, final_response])
    monkeypatch.setattr(chat_agent, "_get_client", lambda: fake_client)

    response = handle_message(batch.batchId, "why is row 2 red?")
    assert response["source"] == "azure_openai"
    assert "streetname" in response["reply"].lower()


def test_llm_handle_failure_reports_explicit_error(monkeypatch):
    batch = _load_mixed_batch()
    configure_fake_azure(monkeypatch, settings)
    monkeypatch.setattr(
        chat_agent, "_get_client", lambda: FakeAzureClient(raises=RuntimeError("bad deployment name"))
    )

    response = handle_message(batch.batchId, "why is row 2 red?")
    assert response["source"] == "azure_openai_error"
    assert "bad deployment name" in response["reply"]
    assert response["errorDetail"] == "bad deployment name"
