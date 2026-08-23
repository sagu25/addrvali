"""
Capability 4: Insights and Explanations.

Turns the already-computed, deterministic ValidationComponentResults into
plain-language narration and a suggested correction. This module NEVER
decides status - finalStatus is fixed before this runs. It only narrates.

Azure OpenAI is the only source of aiExplanation text - there is no
templated stand-in. If Azure OpenAI isn't configured, or a call fails,
aiExplanation is set to an explicit, unmistakable message saying so
(explanationSource = "not_configured" / "azure_openai_error") rather than
silently substituting hand-written text that could be mistaken for a real
explanation.

suggestedCorrection is unrelated to this choice - it's a deterministic
field-level summary built straight from the validation errors/warnings,
never AI-generated, so it's still populated even when Azure is unavailable.
"""

from app.config import settings
from app.models.address_models import RecordValidationResult, ValidationIssue

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    from openai import AzureOpenAI

    _client = AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )
    return _client


def _collect_issues(result: RecordValidationResult) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    for component in (
        result.ruleValidation,
        result.geocodeValidation,
        result.preDispatchValidation,
    ):
        if component is None:
            continue
        errors.extend(component.errors)
        warnings.extend(component.warnings)
    return errors, warnings


def _build_suggested_correction(result: RecordValidationResult) -> dict | None:
    errors, warnings = _collect_issues(result)
    issues = errors or warnings
    if not issues:
        return None
    correction: dict = {}
    for i, issue in enumerate(issues):
        key = issue.fieldName or f"general_{i + 1}"
        correction[key] = issue.message
    return correction


def _call_azure_openai(result: RecordValidationResult) -> str:
    errors, warnings = _collect_issues(result)
    client = _get_client()
    prompt = (
        "You are an assistant narrating address-validation results for a "
        "utility company back-office user. Be concise (2-4 sentences), "
        "plain language, no jargon. Never suggest the record be "
        "auto-approved or auto-submitted - a human always reviews.\n\n"
        f"Final status: {result.finalStatus.value}\n"
        f"Errors: {[e.message for e in errors]}\n"
        f"Warnings: {[w.message for w in warnings]}"
    )
    response = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.2,
    )
    return response.choices[0].message.content


def explain_record(result: RecordValidationResult) -> RecordValidationResult:
    if not settings.azure_openai_configured:
        result.aiExplanation = (
            "Azure OpenAI is not configured - no explanation available. "
            "Set AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY / "
            "AZURE_OPENAI_DEPLOYMENT in backend/.env and restart the server."
        )
        result.explanationSource = "not_configured"
    else:
        try:
            result.aiExplanation = _call_azure_openai(result)
            result.explanationSource = "azure_openai"
        except Exception as exc:
            result.aiExplanation = f"Azure OpenAI explanation failed: {exc}"
            result.explanationSource = "azure_openai_error"

    result.suggestedCorrection = _build_suggested_correction(result)
    return result
