import app.ai.explanations as explanations
from app.config import settings
from app.models.address_models import (
    AddressCombination,
    AddressType,
    BulkAddressCsvRow,
    ValidationStatus,
)
from app.orchestration.record_validator import validate_record

from tests.fake_azure import FakeAzureClient, FakeMessage, FakeResponse, configure_fake_azure


def _red_result():
    row = BulkAddressCsvRow(
        addressType=AddressType.CIVIC,
        addressCombination=AddressCombination.URBAN_STREET,
        houseNumber="17",
        cityTownName="Edmonton",
        province="AB",
        objectId=1,
        servicePointKey="SPK-1",
        distributionSiteId="DSID-1",
        changedBy="tester@atco.com",
    )
    return validate_record(row)


def test_without_azure_configured_explanation_says_so_explicitly():
    result = explanations.explain_record(_red_result())
    assert result.explanationSource == "not_configured"
    assert "not configured" in result.aiExplanation.lower()
    # suggestedCorrection is deterministic, not AI-generated - still populated.
    assert result.suggestedCorrection


def test_azure_success_sets_source_and_text(monkeypatch):
    configure_fake_azure(monkeypatch, settings)
    fake_client = FakeAzureClient(
        responses=[FakeResponse(FakeMessage(content="Row 2 is blocked because the street name is missing."))]
    )
    monkeypatch.setattr(explanations, "_get_client", lambda: fake_client)

    result = explanations.explain_record(_red_result())
    assert result.explanationSource == "azure_openai"
    assert result.aiExplanation == "Row 2 is blocked because the street name is missing."


def test_azure_failure_reports_explicit_error(monkeypatch):
    configure_fake_azure(monkeypatch, settings)
    monkeypatch.setattr(
        explanations, "_get_client", lambda: FakeAzureClient(raises=RuntimeError("401 unauthorized"))
    )

    result = explanations.explain_record(_red_result())
    assert result.explanationSource == "azure_openai_error"
    assert "401 unauthorized" in result.aiExplanation
