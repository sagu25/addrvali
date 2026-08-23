"""
Live Azure OpenAI connectivity check, exposed at GET /api/ai/status.

'Configured' (env vars present and non-placeholder) is not the same as
'working' - a wrong deployment name, an expired key, or a firewalled
endpoint all look 'configured' but fail on the first real call. This
makes one minimal real call and reports exactly what happened, so
whether the app is actually talking to Azure is never a guess.
"""

from app.config import settings


def _mask(value: str, keep: int = 4) -> str:
    if not value:
        return ""
    return value[:keep] + "*" * max(0, len(value) - keep)


def check_azure_openai_status() -> dict:
    result = {
        "configured": settings.azure_openai_configured,
        "endpoint": settings.azure_openai_endpoint or None,
        "deployment": settings.azure_openai_deployment or None,
        "apiKeyPreview": _mask(settings.azure_openai_api_key) or None,
        "liveCallOk": None,
        "liveCallError": None,
        "liveCallReply": None,
    }

    if not settings.azure_openai_configured:
        result["liveCallError"] = (
            "Not configured - AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY / "
            "AZURE_OPENAI_DEPLOYMENT are missing or still placeholders in "
            "backend/.env. The app is using the deterministic fallback for "
            "everything, not Azure OpenAI."
        )
        return result

    try:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=5,
            temperature=0,
        )
        result["liveCallOk"] = True
        result["liveCallReply"] = response.choices[0].message.content
    except Exception as exc:
        result["liveCallOk"] = False
        result["liveCallError"] = f"{type(exc).__name__}: {exc}"

    return result
