import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.ai.chat_agent import handle_message
from app.ai.status_check import check_azure_openai_status
from app.api.chat_formatter import format_chat_message
from app.ingestion.excel_parser import parse_workbook
from app.models.address_models import BulkAddressValidationResponse
from app.orchestration import batch_store
from app.orchestration.batch_validator import validate_batch

router = APIRouter()


class ChatValidateResponse(BaseModel):
    chatMessage: str
    parseErrors: list[dict]
    batch: BulkAddressValidationResponse


@router.post("/chat/validate", response_model=ChatValidateResponse)
async def chat_validate(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Please upload an .xlsx or .xls workbook.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    batch_id = str(uuid.uuid4())

    try:
        parsed = parse_workbook(file_bytes, batch_id=batch_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read workbook: {exc}") from exc

    if not parsed.rows and not parsed.row_errors:
        raise HTTPException(status_code=400, detail="No rows found in the uploaded workbook.")

    batch = validate_batch(parsed.rows, batch_id=batch_id)
    chat_message = format_chat_message(batch, parsed.row_errors)

    return ChatValidateResponse(
        chatMessage=chat_message,
        parseErrors=parsed.row_errors,
        batch=batch,
    )


class ChatMessageRequest(BaseModel):
    batchId: str
    message: str
    history: list[dict] = []


class ChatMessageResponse(BaseModel):
    reply: str
    updatedRecord: dict[str, Any] | None = None
    source: str
    errorDetail: str | None = None


@router.post("/chat/message", response_model=ChatMessageResponse)
async def chat_message(payload: ChatMessageRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if batch_store.get_batch(payload.batchId) is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown batch - upload a workbook first, then ask follow-up questions.",
        )

    result = handle_message(payload.batchId, payload.message, payload.history)
    return ChatMessageResponse(**result)


@router.get("/ai/status")
async def ai_status():
    """
    Definitive answer to 'is this actually calling Azure OpenAI right now?'
    Checks that AZURE_OPENAI_* env vars are set (not placeholders) AND makes
    one real, minimal chat completion call against the configured deployment
    to prove connectivity/auth/deployment-name are actually correct - a
    'configured' flag alone can't catch a wrong deployment name or an
    expired key.
    """
    return check_azure_openai_status()


@router.get("/health")
async def health():
    return {"status": "ok"}
