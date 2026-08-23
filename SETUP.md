# Setup Guide — Address Validation Agent (POC)

Step-by-step instructions to get the backend and frontend running locally
on Windows. For what the project is and how the pieces fit together, see
[`README.md`](README.md).

## Prerequisites

Verified against these versions — newer patch versions should be fine:

| Tool | Version used | Check with |
|---|---|---|
| Python | 3.11.9 | `python --version` |
| Node.js | 22.20.0 | `node --version` |
| npm | 10.9.3 | `npm --version` |

No database, Docker, or external service is required — everything runs
locally and all data is synthetic.

## 1. Backend

Open a terminal in `backend/`.

**1.1 Create and activate a virtual environment**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

**1.2 Install dependencies**

```powershell
pip install -r requirements.txt
```

**1.3 Configure environment variables**

```powershell
copy .env.example .env
```

Leave `.env` as-is for now — Azure OpenAI is optional. With placeholder
values, the app automatically falls back to templated explanations and a
deterministic command parser for follow-up chat (see README → "Follow-up
chat"). Fill in real values later:

```
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

No code or restart-order changes are needed when you add real
credentials — just edit `.env` and restart the server.

**1.4 Generate the synthetic demo workbooks** (first time only)

```powershell
python tests\fixtures\generate_synthetic_workbooks.py
```

Produces three `.xlsx` files in `tests/fixtures/`:
- `clean_urban.xlsx` — 5 valid Urban Street records (all GREEN)
- `clean_rural_road.xlsx` — 5 valid Rural Road records (all GREEN)
- `mixed_batch.xlsx` — 10 records across all 6 address combinations, with
  deliberate rule/geocoding/Maximo failures (3 GREEN / 2 AMBER / 5 RED) —
  use this one for demos

**1.5 Run the tests**

```powershell
pytest -q
```

Expect `28 passed`. If anything fails, fix it before moving on — the
frontend depends on this API contract being correct.

**1.6 Start the server**

```powershell
uvicorn app.main:app --reload --port 8000
```

**1.7 Verify it's up**

```powershell
curl http://127.0.0.1:8000/api/health
```

Expect `{"status":"ok"}`.

## 2. Frontend

Open a **second** terminal in `frontend/` (leave the backend running in
the first one).

**2.1 Install dependencies**

```powershell
npm install
```

**2.2 Configure the API URL**

```powershell
copy .env.example .env
```

Default `VITE_API_BASE_URL=http://localhost:8000` matches the backend
port from step 1.6 — only change this if you ran the backend on a
different port.

**2.3 Start the dev server**

```powershell
npm run dev
```

**2.4 Open it**

Go to `http://localhost:5173`. You should see the chat welcome message.
Upload `backend/tests/fixtures/mixed_batch.xlsx` and confirm you get back
a 🟢 3 / 🟠 2 / 🔴 5 summary with expandable per-row detail.

## 3. Confirm the full loop works

With both servers running:

1. Upload `mixed_batch.xlsx` in the chat.
2. Ask `why is row 9 red?` — should explain the missing Maximo linking
   field.
3. Ask `row 9 distributionSiteId=DSID-3009` — should show a what-if card
   flipping to GREEN, labeled "nothing was saved."

If all three work, the setup is complete.

## Troubleshooting

**`only one usage of each socket address... permitted` on backend start**
Something is already bound to port 8000 — usually a previous `uvicorn`
still running. Find and stop it:

```powershell
netstat -ano | findstr :8000
taskkill /F /PID <pid from previous command>
```

**Chat upload fails with a network/CORS error in the browser console**
Backend isn't running, or `frontend/.env`'s `VITE_API_BASE_URL` doesn't
match the port the backend is actually on. Check `backend/app/config.py`
→ `cors_origins` includes the frontend's origin (defaults to
`http://localhost:5173`).

**"Please upload an .xlsx or .xls workbook" error**
Only Excel workbooks are accepted — CSV isn't wired up in this POC. Use
one of the generated fixtures, or build your own workbook with columns
matching `BulkAddressCsvRow` field names or the ESRI table's business
names (see `backend/app/ingestion/excel_parser.py` → `HEADER_ALIASES`
for the accepted header variants).

**Follow-up chat gives unhelpful answers**
With placeholder Azure OpenAI credentials, the chat runs on a small
deterministic command parser, not free-form understanding — it only
recognizes the exact patterns in the bot's own help text (`row N`,
`row N field=value`, `red/amber/green rows`). Free-form questions need
real Azure OpenAI credentials in `backend/.env`.

## Project structure

```
backend/
  app/
    models/          Pydantic models (BulkAddressCsvRow, RecordValidationResult, ...)
    rules/            Rule matrix + deterministic Rule Validator
    geocoding/         Mocked Geocoding Analyzer
    maximo/            Mocked Maximo Pre-dispatch Check
    orchestration/     Combines checks into Green/Amber/Red + batch store
    ai/                Explanations + follow-up chat agent (tool-calling loop)
    ingestion/         Excel → BulkAddressCsvRow parsing
    api/               FastAPI routes + chat message formatting
  tests/               pytest suite + synthetic fixture generator
frontend/
  src/
    components/        ChatWindow, MessageBubble, RecordDetails
    api/               Backend API client
```
