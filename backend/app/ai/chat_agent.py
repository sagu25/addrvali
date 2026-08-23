"""
Follow-up chat over an already-validated batch.

Azure OpenAI is the only way this answers questions - there is no
command-parser fallback. It runs a real tool-calling loop: the model
decides whether to call get_record / recheck_record / list_records
against the deterministic pipeline and answers from the actual results -
this is the "agentic" piece (the model chooses actions and reasons over
live tool output across turns, instead of narrating a single precomputed
result).

If Azure OpenAI isn't configured, or a call fails, this returns an
explicit, unmistakable message saying so (source = "not_configured" /
"azure_openai_error") rather than silently answering from a regex parser
that could be mistaken for real understanding.
"""

import json

from app.ai import tools as agent_tools
from app.config import settings
from app.orchestration import batch_store

MAX_TOOL_ITERATIONS = 4

SYSTEM_PROMPT = (
    "You are the chat assistant for ATCO's Address Validation Agent. You "
    "help a back-office user understand validation results for a batch "
    "they already uploaded. You have tools to look up a row, simulate a "
    "field change (recheck_record), and list rows by status - always use "
    "the tools rather than guessing at data you don't have. Never say a "
    "record has been approved, submitted, or dispatched - all actions "
    "remain advisory and a human still controls the real GIS/Maximo "
    "update. Keep answers to 2-4 sentences unless the user asks for a list."
)

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


def _llm_handle(batch_id: str, message: str, history: list[dict]) -> dict:
    client = _get_client()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    last_recheck_payload = None

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=messages,
            tools=agent_tools.TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.1,
            max_tokens=400,
        )
        choice = response.choices[0].message

        if not choice.tool_calls:
            return {
                "reply": choice.content or "I don't have a response for that.",
                "updatedRecord": last_recheck_payload,
            }

        messages.append(
            {
                "role": "assistant",
                "content": choice.content,
                "tool_calls": [tc.model_dump() for tc in choice.tool_calls],
            }
        )

        for tool_call in choice.tool_calls:
            args = json.loads(tool_call.function.arguments or "{}")
            result = agent_tools.call_tool(tool_call.function.name, batch_id, args)
            if tool_call.function.name == "recheck_record" and "error" not in result:
                last_recheck_payload = result
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                }
            )

    return {
        "reply": "I looked into this but couldn't reach a final answer in time - try a more specific question.",
        "updatedRecord": last_recheck_payload,
    }


def handle_message(batch_id: str, message: str, history: list[dict] | None = None) -> dict:
    if batch_store.get_batch(batch_id) is None:
        return {
            "reply": "I don't have that batch anymore - please upload the workbook again.",
            "updatedRecord": None,
            "source": "no_batch",
        }

    if not settings.azure_openai_configured:
        return {
            "reply": (
                "Azure OpenAI is not configured, so I can't answer questions "
                "yet. Set AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY / "
                "AZURE_OPENAI_DEPLOYMENT in backend/.env and restart the "
                "server, then check GET /api/ai/status to confirm."
            ),
            "updatedRecord": None,
            "source": "not_configured",
        }

    try:
        result = _llm_handle(batch_id, message, history or [])
        result["source"] = "azure_openai"
        return result
    except Exception as exc:
        return {
            "reply": f"Azure OpenAI call failed: {exc}",
            "updatedRecord": None,
            "source": "azure_openai_error",
            "errorDetail": str(exc),
        }
