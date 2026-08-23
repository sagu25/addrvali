"""
Follow-up chat over an already-validated batch.

When Azure OpenAI is configured, this runs a real tool-calling loop: the
model decides whether to call get_record / recheck_record / list_records
against the deterministic pipeline and answers from the actual results -
this is the "agentic" piece (the model chooses actions and reasons over
live tool output across turns, instead of narrating a single precomputed
result).

Without Azure OpenAI configured, falls back to a small deterministic
command parser covering the same three tools so the chat still works
end-to-end with placeholder credentials. Its supported syntax is
intentionally explicit (see HELP_TEXT) rather than open-ended NLP.
"""

import json
import re

from app.ai import tools as agent_tools
from app.config import settings
from app.models.address_models import RecordValidationResult
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

HELP_TEXT = (
    "I can answer questions about the batch you just uploaded. Try:\n"
    "  - \"row 3\" - explain why a row has its status\n"
    "  - \"row 9 distributionSiteId=DSID-3009\" - simulate fixing a field and re-check it\n"
    "  - \"red rows\" / \"amber rows\" / \"green rows\" - list rows by status\n"
    "(Azure OpenAI isn't configured, so I'm using a simple command parser "
    "instead of free-form understanding - these exact patterns work best.)"
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


_ROW_PATTERN = re.compile(r"\brow\s*#?\s*(\d+)|record\s*#?\s*(\d+)|#(\d+)", re.I)
_FIELD_VALUE_PATTERN = re.compile(r"([a-zA-Z /\-]+?)\s*[:=]\s*(.+)$")
_STATUS_WORDS = {"green": "GREEN", "amber": "AMBER", "red": "RED"}


def _fallback_handle(batch_id: str, message: str) -> dict:
    lowered = message.strip().lower()

    row_match = _ROW_PATTERN.search(message)

    # Only treat this as a "list rows by status" request when no specific
    # row was mentioned - otherwise "why is row 2 red?" would list every
    # RED row instead of answering about row 2.
    if not row_match:
        for word, status in _STATUS_WORDS.items():
            if word in lowered:
                result = agent_tools.list_records(batch_id, status)
                if "error" in result:
                    return {"reply": result["error"], "updatedRecord": None}
                if result["count"] == 0:
                    return {"reply": f"No {status} rows in this batch.", "updatedRecord": None}
                lines = [f"{status} rows ({result['count']}):"]
                lines.extend(f"  - Row {r['rowId']} ({r['servicePointKey'] or 'no key'})" for r in result["rows"])
                return {"reply": "\n".join(lines), "updatedRecord": None}
        return {"reply": HELP_TEXT, "updatedRecord": None}

    row_id = int(next(g for g in row_match.groups() if g))
    remainder = message[row_match.end():].strip(" ,.-")

    field_match = _FIELD_VALUE_PATTERN.match(remainder) if remainder else None
    if field_match:
        raw_field, value = field_match.group(1).strip(), field_match.group(2).strip()
        result = agent_tools.recheck_record(batch_id, row_id, {raw_field: value})
        if "error" in result:
            return {"reply": result["error"], "updatedRecord": None}
        status = result["finalStatus"]
        return {
            "reply": (
                f"If row {row_id} had {raw_field} = \"{value}\", it would validate as "
                f"{status}. {result.get('aiExplanation', '')}\n(This is a what-if check only - nothing was saved.)"
            ),
            "updatedRecord": result,
        }

    result = agent_tools.get_record(batch_id, row_id)
    if "error" in result:
        return {"reply": result["error"], "updatedRecord": None}
    explanation = result.get("aiExplanation") or f"Row {row_id} is {result['finalStatus']}."
    return {"reply": explanation, "updatedRecord": None}


def handle_message(batch_id: str, message: str, history: list[dict] | None = None) -> dict:
    if batch_store.get_batch(batch_id) is None:
        return {
            "reply": "I don't have that batch anymore - please upload the workbook again.",
            "updatedRecord": None,
            "source": "no_batch",
        }

    if settings.azure_openai_configured:
        try:
            result = _llm_handle(batch_id, message, history or [])
            result["source"] = "azure_openai"
            return result
        except Exception as exc:  # fall back rather than break the chat
            fallback = _fallback_handle(batch_id, message)
            fallback["reply"] = (
                f"(Azure OpenAI call failed, falling back to command parsing: {exc})\n\n"
                + fallback["reply"]
            )
            fallback["source"] = "fallback_after_azure_error"
            fallback["errorDetail"] = str(exc)
            return fallback

    result = _fallback_handle(batch_id, message)
    result["source"] = "fallback_parser"
    return result
