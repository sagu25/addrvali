# Address Validation Agent — POC

A chat-style agent: upload an Excel workbook of Legal/Civic/Rural address
records, the agent validates each row against ATCO's rule matrix, a mocked
geocoder, and a mocked Maximo pre-dispatch check, then replies in the chat
with a Green/Amber/Red summary and per-record detail. Read-only and
advisory only — it never writes to GIS/Maximo, matching the SOW's scope
(see `backend/app/rules/matrix.py` docstring for the rule source and known
gaps).

All data is synthetic. The geocoder and Maximo check are mocked (see
`backend/app/geocoding/mock_geocoder.py` and `backend/app/maximo/predispatch.py`)
until real ATCO endpoints are confirmed.

## Stack

- **Backend**: FastAPI + Pydantic (Python 3.11+)
- **Frontend**: React + Vite
- **AI (explanations only)**: Azure OpenAI, optional — falls back to
  templated text if credentials aren't set, so the POC runs standalone.

For step-by-step install and run instructions, see
[`SETUP.md`](SETUP.md). The quick version:

## Backend setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # fill in Azure OpenAI creds later; POC runs without them
uvicorn app.main:app --reload --port 8000
```

Run tests:

```bash
pytest -q
```

Regenerate the synthetic demo workbooks:

```bash
python tests/fixtures/generate_synthetic_workbooks.py
```

This produces `tests/fixtures/clean_urban.xlsx`, `clean_rural_road.xlsx`, and
`mixed_batch.xlsx` (10 rows covering all 6 address combinations with a mix
of GREEN/AMBER/RED outcomes) — use these to try the chat UI.

## Frontend setup

```bash
cd frontend
npm install
cp .env.example .env    # VITE_API_BASE_URL, defaults to http://localhost:8000
npm run dev
```

Open `http://localhost:5173`, upload one of the fixture workbooks from
`backend/tests/fixtures/`, and the agent replies in the chat with a
summary and expandable per-row detail.

## Follow-up chat (the agentic part)

After a batch is uploaded, ask follow-up questions in the same chat instead
of re-reading the table yourself. The model doesn't just narrate the
precomputed result — it calls back into the deterministic pipeline live:

- `"why is row 3 red?"` → looks up that row's actual errors
- `"row 9 distributionSiteId=DSID-3009"` → **simulates** the field change and
  re-runs rules + geocoding + Maximo readiness against the hypothetical
  value (never saves it — matches "explains, never decides")
- `"which rows are red?"` → lists rows filtered by status

With `AZURE_OPENAI_*` configured in `backend/.env`, this runs as a real
OpenAI tool-calling loop (`backend/app/ai/chat_agent.py`) — the model
decides which tool to call and reasons over the live result. Without
credentials, a small deterministic command parser covers the same three
tools so the chat still works end-to-end; it only understands the explicit
patterns above (see the bot's own help text if you send an unrecognised
message).

## How synthetic outcomes are controlled

Since there's no real geocoder or Maximo to call, the mocks read magic
tokens out of the address text / key fields so demo outcomes are
repeatable instead of random:

| Token (anywhere in the relevant field) | Effect |
|---|---|
| `NOMATCH` in street/road fields | Geocoder finds no match → RED |
| `LOWCONF` in street/road fields | Low geocoder confidence → RED |
| `ALT` in street/road fields | Moderate confidence + alternates → AMBER |
| `DRIFT` in street/road fields | Match found but far from expected location → AMBER |
| `MAXCONFLICT` in servicePointKey/distributionSiteId | Simulated Maximo schema conflict → RED |
| missing servicePointKey/distributionSiteId/objectId/changedBy | Maximo payload incomplete → RED |

Everything else is checked deterministically against the rule matrix
(`backend/app/rules/matrix.py`) for the row's declared `addressCombination`.

## Known gaps / before this goes beyond POC

- **Rule matrix rows 30–31** (between Government Plan ID and Address Lot
  ID) weren't captured in the source screenshot — confirm with the
  signed-off matrix before treating `rules/matrix.py` as final.
- The Rural Street combination has a footnote in the source table about a
  conditional rule ("if one optional field is populated, all required
  fields for that combination must be populated") that isn't encoded yet
  — currently the base Required/Optional/Not-Allowed grid is enforced as-is.
- Geocoding and Maximo pre-dispatch are mocked; swapping in ATCO's real
  geocoder and Maximo REST contract only requires replacing
  `mock_geocoder.py` / `predispatch.py` — the `ValidationComponentResult`
  contract they return stays the same.
- Post-update Reconciliation (capability 6 in the SOW) isn't built — it
  needs real GIS/Maximo read access to be meaningful.
