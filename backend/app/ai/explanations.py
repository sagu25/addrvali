"""
Capability 4: Insights and Explanations.

Turns the already-computed, deterministic ValidationComponentResults into
plain-language narration and a suggested correction. This module NEVER
decides status - finalStatus is fixed before this runs. It only narrates.

Uses Azure OpenAI when AZURE_OPENAI_* env vars are configured; otherwise
falls back to templated text so the POC runs end-to-end with placeholder
credentials. Any Azure OpenAI call failure also falls back to the template
rather than breaking the pipeline.
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


def _template_explanation(result: RecordValidationResult) -> str:
    errors, warnings = _collect_issues(result)
    row_label = f"row {result.rowId}" if result.rowId is not None else "this record"

    if result.finalStatus.value == "GREEN":
        return f"{row_label.capitalize()} passed all checks and is ready for the governed dispatch channel."

    lines = [f"{row_label.capitalize()} is {result.finalStatus.value}."]
    if errors:
        lines.append("Blocking issues:")
        lines.extend(f"  - {issue.message}" for issue in errors)
    if warnings:
        lines.append("Needs review:")
        lines.extend(f"  - {issue.message}" for issue in warnings)
    return "\n".join(lines)


def _template_suggested_correction(result: RecordValidationResult) -> dict | None:
    errors, warnings = _collect_issues(result)
    issues = errors or warnings
    if not issues:
        return None
    correction: dict = {}
    for i, issue in enumerate(issues):
        key = issue.fieldName or f"general_{i + 1}"
        correction[key] = issue.message
    return correction


def _llm_explanation(result: RecordValidationResult) -> str | None:
    if not settings.azure_openai_configured:
        return None
    try:
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
    except Exception:
        return None


def explain_record(result: RecordValidationResult) -> RecordValidationResult:
    explanation = _llm_explanation(result) or _template_explanation(result)
    result.aiExplanation = explanation
    result.suggestedCorrection = _template_suggested_correction(result)
    return result
