from app.models.address_models import AddressCombination, AddressType, BulkAddressCsvRow, ValidationStatus
from app.rules.validator import validate_record


def test_urban_street_clean_is_green():
    row = BulkAddressCsvRow(
        addressType="Civic",
        addressCombination=AddressCombination.URBAN_STREET,
        houseNumber="100",
        streetName="Maple Street",
        cityTownName="Calgary",
        province="AB",
    )
    result = validate_record(row)
    assert result.status == ValidationStatus.GREEN
    assert result.errors == []


def test_urban_street_missing_required_street_name_is_red():
    row = BulkAddressCsvRow(
        addressType="Civic",
        addressCombination=AddressCombination.URBAN_STREET,
        houseNumber="17",
        cityTownName="Edmonton",
        province="AB",
    )
    result = validate_record(row)
    assert result.status == ValidationStatus.RED
    assert any(e.fieldName == "streetName" for e in result.errors)


def test_lld_lsd_not_allowed_field_populated_is_red():
    row = BulkAddressCsvRow(
        addressType="Legal",
        addressCombination=AddressCombination.LLD_ATS_LSD,
        lsd="04",
        section="12",
        township="45",
        range="10",
        meridian="W4",
        province="AB",
        cityTownName="Should Not Be Here",
    )
    result = validate_record(row)
    assert result.status == ValidationStatus.RED
    assert any(e.fieldName == "cityTownName" for e in result.errors)


def test_lot_block_plan_clean_is_green():
    row = BulkAddressCsvRow(
        addressType="Legal",
        addressCombination=AddressCombination.LOT_BLOCK_PLAN,
        legalLot="7",
        block="3",
        governmentPlanId="8021144",
        cityTownName="Red Deer",
        province="AB",
    )
    result = validate_record(row)
    assert result.status == ValidationStatus.GREEN


def test_rural_road_requires_pre_road_and_road_type():
    row = BulkAddressCsvRow(
        addressType="Rural",
        addressCombination=AddressCombination.RURAL_ROAD,
        province="AB",
    )
    result = validate_record(row)
    assert result.status == ValidationStatus.RED
    missing_fields = {e.fieldName for e in result.errors}
    assert "addressPreRoadNumber" in missing_fields
    assert "addressRoadType" in missing_fields
    assert "addressPostRoadNumber" in missing_fields


def test_missing_address_combination_is_red():
    row = BulkAddressCsvRow(addressType="Civic")
    result = validate_record(row)
    assert result.status == ValidationStatus.RED
