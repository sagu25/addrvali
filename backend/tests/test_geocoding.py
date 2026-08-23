from app.models.address_models import AddressCombination, BulkAddressCsvRow, ValidationStatus
from app.geocoding.mock_geocoder import analyze


def _row(street_name: str) -> BulkAddressCsvRow:
    return BulkAddressCsvRow(
        addressType="Civic",
        addressCombination=AddressCombination.URBAN_STREET,
        houseNumber="100",
        streetName=street_name,
        cityTownName="Calgary",
        province="AB",
    )


def test_clean_address_is_green():
    result = analyze(_row("Maple Street"))
    assert result.status == ValidationStatus.GREEN


def test_nomatch_token_is_red():
    result = analyze(_row("NOMATCH Lane"))
    assert result.status == ValidationStatus.RED


def test_lowconf_token_is_red():
    result = analyze(_row("LOWCONF Lane"))
    assert result.status == ValidationStatus.RED


def test_alt_token_is_amber():
    result = analyze(_row("ALT Lane"))
    assert result.status == ValidationStatus.AMBER


def test_drift_token_is_amber():
    result = analyze(_row("DRIFT Lane"))
    assert result.status == ValidationStatus.AMBER
    assert result.metadata["driftDetected"] is True


def test_same_address_is_deterministic():
    result_a = analyze(_row("Maple Street"))
    result_b = analyze(_row("Maple Street"))
    assert result_a.metadata["coordinates"] == result_b.metadata["coordinates"]
