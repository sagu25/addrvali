from app.models.address_models import AddressCombination, BulkAddressCsvRow, ValidationStatus
from app.maximo.predispatch import check


def _base_row(**overrides) -> BulkAddressCsvRow:
    defaults = dict(
        addressType="Civic",
        addressCombination=AddressCombination.URBAN_STREET,
        objectId=1,
        servicePointKey="SPK-1",
        distributionSiteId="DSID-1",
        changedBy="tester@atco.com",
    )
    defaults.update(overrides)
    return BulkAddressCsvRow(**defaults)


def test_complete_linking_fields_is_green():
    result = check(_base_row())
    assert result.status == ValidationStatus.GREEN


def test_missing_distribution_site_id_is_red():
    result = check(_base_row(distributionSiteId=None))
    assert result.status == ValidationStatus.RED
    assert any(e.fieldName == "distributionSiteId" for e in result.errors)


def test_maxconflict_token_is_red():
    result = check(_base_row(servicePointKey="SPK-MAXCONFLICT-1"))
    assert result.status == ValidationStatus.RED
