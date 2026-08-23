import os

from app.ingestion.excel_parser import parse_workbook
from app.models.address_models import ValidationStatus
from app.orchestration.batch_validator import validate_batch

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def test_clean_urban_workbook_is_all_green():
    with open(os.path.join(FIXTURES_DIR, "clean_urban.xlsx"), "rb") as f:
        parsed = parse_workbook(f.read())
    batch = validate_batch(parsed.rows)
    assert batch.totalRecords == 5
    assert batch.greenCount == 5
    assert batch.amberCount == 0
    assert batch.redCount == 0


def test_mixed_batch_workbook_has_expected_distribution():
    with open(os.path.join(FIXTURES_DIR, "mixed_batch.xlsx"), "rb") as f:
        parsed = parse_workbook(f.read())
    batch = validate_batch(parsed.rows)
    assert batch.totalRecords == 10
    # rows 1,3,5 clean -> GREEN ; rows 6,7 -> AMBER ; rows 2,4,8,9,10 -> RED
    assert batch.greenCount == 3
    assert batch.amberCount == 2
    assert batch.redCount == 5
    for record in batch.results:
        assert record.aiExplanation, f"row {record.rowId} missing explanation"


def test_every_non_green_record_has_a_reason():
    with open(os.path.join(FIXTURES_DIR, "mixed_batch.xlsx"), "rb") as f:
        parsed = parse_workbook(f.read())
    batch = validate_batch(parsed.rows)
    for record in batch.results:
        if record.finalStatus != ValidationStatus.GREEN:
            assert record.suggestedCorrection, f"row {record.rowId} missing suggested correction"
