# Address Validation Agent — Architecture & Design Documentation

This document explains what was built, why it's structured the way it is,
and how every piece fits together. Read this to understand the system;
read [`SETUP.md`](SETUP.md) to run it; read [`README.md`](README.md) for
the short version.

---

## 1. What this project is

ATCO (a utility) issued an SOW for an **Address Validation Agent**: a
read-only, advisory layer that checks proposed Legal/Civic/Rural address
updates against ATCO's approved business rules, geocoding confidence, and
Maximo dispatch readiness — before those updates go through ATCO's
existing (unmodified) GIS/Maximo update channel. The SOW's core principle,
which every design decision below traces back to:

> **The Agent explains, never decides.** It is read-only, keeps the human
> in control, and introduces no new write path to GIS or Maximo.

The full SOW scoped this as a layer embedded in ATCO's existing ArcGIS
Experience Builder application, with Service Point search, real GIS/Maximo
connectivity, and post-update reconciliation. **This project builds one
slice of that**: the validation engine itself, exposed through a
standalone React chat interface instead of the Experience Builder
embedding — a deliberate scope choice, not an oversight (see §8).

### The source material

Three inputs shaped this build, all supplied as photos of existing ATCO
documents (kept out of the git repo — see `.gitignore` — since they
contain ATCO-internal content):

1. **The SOW** — business need, agent scope (in/out of bounds), the six
   functional capabilities, the traffic-light decision model, and
   functional/technical requirements.
2. **The ESRI Address Validation rule matrix** — a table defining, for six
   address "combinations" (Urban Street, LLD/ATS-Quarter, LLD/ATS-LSD, Lot
   Block Plan, Rural Road, Rural Street), which of ~28 fields are
   Required / Optional / Not Allowed / N/A. This became
   `backend/app/rules/matrix.py`.
3. **An existing partial FastAPI project** (`testagent`) with Pydantic
   models already sketched out for this domain — ported and extended into
   `backend/app/models/address_models.py`.

---

## 2. High-level architecture

```
┌─────────────────────┐        HTTP/JSON         ┌──────────────────────────┐
│   React chat UI      │ ───────────────────────▶ │   FastAPI backend         │
│   (frontend/)         │ ◀─────────────────────── │   (backend/)               │
└─────────────────────┘                           └──────────────────────────┘
                                                              │
                                     ┌────────────────────────┼────────────────────────┐
                                     ▼                        ▼                        ▼
                          ┌─────────────────┐      ┌──────────────────┐    ┌──────────────────┐
                          │ Rule Validator    │      │ Geocoding         │    │ Pre-dispatch       │
                          │ (real logic,       │      │ Analyzer          │    │ Check              │
                          │  deterministic)    │      │ (MOCKED)          │    │ (MOCKED)           │
                          └─────────────────┘      └──────────────────┘    └──────────────────┘
                                     │                        │                        │
                                     └────────────────────────┼────────────────────────┘
                                                              ▼
                                                 ┌──────────────────────────┐
                                                 │ Orchestration               │
                                                 │ Green/Amber/Red rollup      │
                                                 └──────────────────────────┘
                                                              │
                                                              ▼
                                                 ┌──────────────────────────┐
                                                 │ Azure OpenAI (required,     │
                                                 │ no fallback)                │
                                                 │ - explanations               │
                                                 │ - follow-up chat            │
                                                 │   (tool-calling loop)       │
                                                 └──────────────────────────┘
```

**The critical architectural boundary**: status (Green/Amber/Red) is
decided entirely by the three deterministic components on the left/center
*before* Azure OpenAI is ever called. The LLM narrates a decision that
already exists and answers questions by calling back into the same
deterministic functions — it cannot itself change a record's status. This
is not a convention, it's enforced structurally: `explain_record()` and
`handle_message()` both receive an already-final `RecordValidationResult`
and only ever *read* from it or *simulate* a hypothetical variant (never
mutate the stored original — see §5.6).

---

## 3. Repository layout

```
ADDR/
├── README.md              What the project is, quick start
├── SETUP.md                Step-by-step install/run/troubleshoot
├── ARCHITECTURE.md          This file
├── .gitignore                Excludes venv, node_modules, .env, source screenshots
│
├── backend/
│   ├── app/
│   │   ├── main.py                    FastAPI app, CORS setup
│   │   ├── config.py                   Env var loading, Settings singleton
│   │   ├── models/
│   │   │   └── address_models.py        All Pydantic models (§4)
│   │   ├── rules/
│   │   │   ├── matrix.py                 The transcribed ESRI rule matrix (data)
│   │   │   └── validator.py              Capability 1: Rule Validator (logic)
│   │   ├── geocoding/
│   │   │   └── mock_geocoder.py          Capability 2: Geocoding Analyzer (MOCKED)
│   │   ├── maximo/
│   │   │   └── predispatch.py            Capability 3: Pre-dispatch Check (MOCKED)
│   │   ├── orchestration/
│   │   │   ├── record_validator.py       Combines 1+2+3 → one record's status
│   │   │   ├── batch_validator.py        Capability 5: runs record_validator over a batch
│   │   │   └── batch_store.py            In-memory batch storage (for follow-up chat)
│   │   ├── ai/
│   │   │   ├── explanations.py           Capability 4: Azure OpenAI narration (required)
│   │   │   ├── chat_agent.py             Follow-up chat: Azure tool-calling loop
│   │   │   ├── tools.py                  The 3 tools the chat model can call
│   │   │   └── status_check.py           Live Azure OpenAI connectivity test
│   │   ├── ingestion/
│   │   │   └── excel_parser.py           .xlsx → BulkAddressCsvRow, header aliasing
│   │   └── api/
│   │       ├── routes.py                 HTTP endpoints
│   │       └── chat_formatter.py         Structured result → chat-readable text
│   ├── tests/                            32 pytest tests + synthetic fixtures
│   ├── requirements.txt
│   └── .env.example                      Template for AZURE_OPENAI_* / CORS_ORIGINS
│
└── frontend/
    ├── src/
    │   ├── App.jsx / App.css              Shell + chat styling
    │   ├── components/
    │   │   ├── ChatWindow.jsx              Upload + text input, message list, state
    │   │   ├── MessageBubble.jsx           Renders one chat message + source badge
    │   │   └── RecordDetails.jsx           Expandable per-row validation detail
    │   └── api/client.js                   Fetch wrappers for the two endpoints
    └── .env.example                        VITE_API_BASE_URL
```

---

## 4. Data models (`backend/app/models/address_models.py`)

Everything in the system flows through these Pydantic models. Understanding
them first makes every other module easier to read.

| Model | Purpose |
|---|---|
| `AddressType` (enum) | `Civic` / `Legal` / `Rural` — the top-level address category |
| `AddressCombination` (enum) | The 6 rule-matrix combinations: `URBAN_STREET`, `LLD_ATS_QUARTER`, `LLD_ATS_LSD`, `LOT_BLOCK_PLAN`, `RURAL_ROAD`, `RURAL_STREET` |
| `ValidationSeverity` (enum) | `ERROR` / `WARNING` / `INFO` — per-issue |
| `ValidationStatus` (enum) | `GREEN` / `AMBER` / `RED` — the traffic-light model |
| `BulkAddressCsvRow` | One input row: every possible address field (house number, street name, LSD, section/township/range/meridian, lot/block/plan, rural road fields, etc.) plus linking fields (`servicePointKey`, `distributionSiteId`, `objectId`) |
| `ValidationIssue` | One error/warning: field name + message + severity |
| `ValidationComponentResult` | Output of *one* check (rule/geocode/pre-dispatch): status + errors + warnings + metadata |
| `RecordValidationResult` | The full per-row result: all three component results, the final rollup status, AI explanation + its source, suggested correction |
| `BulkAddressValidationResponse` | The full batch result: counts + list of `RecordValidationResult` |

**Field validators worth knowing about** (all `mode="before"`, meaning they
run on raw input before type coercion):
- `normalise_address_type` — accepts `"Civic"`, `"Civil"`, `"Urban"` (all →
  `CIVIC`), `"Legal"`, `"Rural"`; case-insensitive. Also explicitly
  short-circuits if already an `AddressType` instance — this was a real
  bug (see §9) because `str(AddressType.CIVIC)` doesn't return `"Civic"`
  for a plain `(str, Enum)` class, it returns `"AddressType.CIVIC"`, which
  broke every round-trip through `model_dump()` → reconstruct.
- `normalise_province` / `normalise_postal_code` — uppercase + strip
  whitespace (postal code also strips internal spaces).

---

## 5. Backend components in detail

### 5.1 Rule Validator — `rules/matrix.py` + `rules/validator.py`

**This is the one component that's "real," not mocked.** `matrix.py` is
pure data: a dict keyed by `AddressCombination` name → field name →
`FieldRule` (`REQUIRED` / `OPTIONAL` / `NOT_ALLOWED` / `N/A`), transcribed
directly from the ESRI table screenshot. `validator.py` is pure logic: for
a given row, look up its combination's rule set, and for every field in
`FIELD_ORDER`, check the populated/not-populated state against the rule:

- `REQUIRED` + not populated → error
- `NOT_ALLOWED` or `N/A` + populated → error
- `OPTIONAL` → no check either way

Any error → `RED`. No errors → `GREEN` (this component never produces
`AMBER` — ambiguity only comes from geocoding/Maximo).

**Known gap, documented in the file itself**: rows 30–31 of the source
table (between "Government Plan ID" and "Address Lot ID") weren't visible
in the source screenshot. There's also an unencoded footnote about a
conditional rule on the Rural Street combination. Both are flagged as
TODOs rather than guessed at — confirm against the signed-off matrix
before this goes past POC.

### 5.2 Geocoding Analyzer — `geocoding/mock_geocoder.py` (MOCKED)

Simulates ATCO's real geocoder, which isn't accessible from this POC.
Deterministic, not random: builds an address string from the row, hashes
it (`sha256`) to derive stable fake coordinates, and checks for magic
tokens anywhere in the text to force a specific scenario:

| Token | Simulated outcome |
|---|---|
| `NOMATCH` | No candidate found → `RED` |
| `LOWCONF` | Low-confidence single match → `RED` |
| `ALT` | Moderate confidence + alternate candidates → `AMBER` |
| `DRIFT` | Match found, but far from expected location → `AMBER` |
| *(none)* | High-confidence single match → `GREEN` |

This is swappable: replace the body of `analyze()` with a real HTTP call
to ATCO's geocoder — the `ValidationComponentResult` contract it returns
doesn't need to change.

### 5.3 Pre-dispatch Check — `maximo/predispatch.py` (MOCKED)

Simulates whether the record's Maximo payload would be accepted, using a
small synthetic "required linking fields" schema (`servicePointKey`,
`distributionSiteId`, `objectId`, `changedBy`) rather than ATCO's real
Maximo contract. Missing any → `RED`. Also honors a `MAXCONFLICT` magic
token in `servicePointKey`/`distributionSiteId` to simulate a schema
conflict. Same swap-out story as the geocoder.

### 5.4 Orchestration — `orchestration/`

- **`record_validator.py`** — runs all three checks above for one row and
  rolls them into a single `finalStatus`: worst-of-three
  (`RED` > `AMBER` > `GREEN`).
- **`batch_validator.py`** — capability 5 (Batch Analysis): runs
  `record_validator` over every row, calls `explain_record()` on each,
  tallies Green/Amber/Red counts, and — important — **persists the batch**
  into `batch_store` before returning, so follow-up chat questions can
  reference it later without the row data being re-uploaded.
- **`batch_store.py`** — a plain in-memory dict keyed by `batchId`. POC-
  scoped deliberately: no persistence, no eviction, single-process. A real
  deployment would back this with a session store or short-TTL cache
  (this is also where "auditability" would need real work — see §8).

### 5.5 AI layer — `ai/` (Azure OpenAI only, no fallback)

This is the layer that changed the most during development — see §9 for
the story. Current design, as of the "no fallback" decision:

- **`explanations.py`** (capability 4) — takes an already-decided
  `RecordValidationResult` and asks Azure OpenAI to phrase it in plain
  language. **If Azure isn't configured, or the call fails, this does
  NOT substitute template text** — it sets `aiExplanation` to an explicit
  message saying so, and `explanationSource` to `"not_configured"` or
  `"azure_openai_error"` (vs. `"azure_openai"` on success). This was a
  deliberate reversal of an earlier design (see §9) — the goal is that a
  broken/missing integration is *visibly* broken, never silently papered
  over with plausible-looking text.
  `suggestedCorrection` is a separate, always-on, non-AI field: a
  deterministic dict built straight from the validation errors.

- **`chat_agent.py`** — the follow-up chat, and the part that's actually
  "agentic" in the strict sense: given a user message, it runs a real
  **tool-calling loop** against Azure OpenAI (`tools=agent_tools.TOOL_SCHEMAS`,
  `tool_choice="auto"`, up to `MAX_TOOL_ITERATIONS=4` rounds). The model
  decides which tool to call, reads the real result, and can decide to
  call another tool before finally answering — this is meaningfully
  different from narrating a single precomputed blob, because the model is
  choosing actions and reasoning over live tool output. Same no-fallback
  policy: not configured / call failure → explicit message, `source` field
  set accordingly (`"azure_openai"` / `"not_configured"` /
  `"azure_openai_error"` / `"no_batch"`).

- **`tools.py`** — the three functions the model can call, and their
  JSON-schema definitions:
  - `get_record(batchId, rowId)` — read-only lookup from `batch_store`.
  - `recheck_record(batchId, rowId, fieldUpdates)` — **the what-if
    simulator**. Takes the *original* stored row, merges in the
    hypothetical field changes, re-runs the full deterministic pipeline
    against a *new, separate* `BulkAddressCsvRow` instance, and returns
    the result. Never writes back to `batch_store` — this is the concrete
    code-level enforcement of "explains, never decides": there is no
    function anywhere in this codebase that persists a correction.
    Field names are resolved leniently via the same `HEADER_ALIASES` used
    by Excel ingestion, so `"postal code"` and `"postalCode"` both work.
  - `list_records(batchId, status)` — filtered listing.

- **`status_check.py`** — `GET /api/ai/status`. Distinguishes "configured"
  (env vars present, not placeholders) from "actually working" (a real
  minimal call to the deployment succeeds) — because a wrong deployment
  name or expired key still looks "configured." Returns a masked key
  preview, and on failure, the *actual* exception message from Azure.

### 5.6 Ingestion — `ingestion/excel_parser.py`

Reads an uploaded `.xlsx`/`.xls` via `pandas`, and maps column headers to
`BulkAddressCsvRow` field names through `HEADER_ALIASES` — a dict
supporting both the model's own field names (`houseNumber`) and the ESRI
table's business names (`"House Number"`), case-insensitively. Rows that
fail Pydantic validation (most commonly: missing `addressType`) are
collected as `row_errors` and excluded from the batch, rather than failing
the whole upload.

### 5.7 API layer — `api/`

Two endpoints, both under `/api`:

- **`POST /chat/validate`** — multipart file upload. Validates file type/
  non-empty, parses it, runs `validate_batch`, formats a chat-readable
  summary via `chat_formatter.py`, returns `{chatMessage, parseErrors, batch}`.
- **`POST /chat/message`** — JSON `{batchId, message, history}`. Looks up
  the batch in `batch_store` (404 if unknown), calls `handle_message()`,
  returns `{reply, updatedRecord, source, errorDetail}`.
- **`GET /ai/status`** — the live connectivity check (§5.5).
- **`GET /health`** — trivial liveness check.

`chat_formatter.py` deserves a specific note: it does **not** just dump
`aiExplanation` into the summary line — it pulls the first real error/
warning message directly from the component results
(`_first_issue_message`), because early on `aiExplanation`'s first line
was just a generic status header ("Row 2 is RED.") with the actual reason
on a later line — a real bug caught by testing against live output, not
just reading the code (see §9).

---

## 6. Request flow

### 6.1 Batch upload (`POST /api/chat/validate`)

```
User selects .xlsx in chat → ChatWindow.jsx uploads via multipart
  → routes.chat_validate()
    → excel_parser.parse_workbook()          [rows: List[BulkAddressCsvRow], row_errors]
    → batch_validator.validate_batch(rows)
        for each row:
          → record_validator.validate_record(row)
              → rules.validator.validate_record()        → ValidationComponentResult
              → mock_geocoder.analyze()                   → ValidationComponentResult
              → predispatch.check()                        → ValidationComponentResult
              → rollup → finalStatus
          → explanations.explain_record(result)            → aiExplanation, explanationSource
        → tally counts, batch_store.save_batch()
    → chat_formatter.format_chat_message()      → human-readable summary string
  ← {chatMessage, parseErrors, batch: BulkAddressValidationResponse}
→ ChatWindow renders bot bubble + expandable RecordDetails per row
```

### 6.2 Follow-up chat (`POST /api/chat/message`)

```
User types "why is row 9 red?" → ChatWindow sends {batchId, message, history}
  → routes.chat_message()
    → chat_agent.handle_message()
        if batch unknown → {source: "no_batch"}
        if Azure not configured → {source: "not_configured"}
        else:
          → chat_agent._llm_handle()
              loop (max 4 rounds):
                → Azure OpenAI chat.completions.create(tools=[...], tool_choice="auto")
                if model requests a tool call:
                  → tools.call_tool(name, batchId, args)   # get_record / recheck_record / list_records
                  → feed tool result back to the model, continue loop
                else:
                  → return model's final text as the reply
          → {source: "azure_openai"} or {source: "azure_openai_error", errorDetail}
  ← {reply, updatedRecord, source, errorDetail}
→ ChatWindow appends bot bubble with source badge + RecordRow if updatedRecord present
```

---

## 7. Frontend architecture

Plain React + Vite, no state management library — the whole chat fits in
one component's `useState`/`useRef`:

- **`ChatWindow.jsx`** — owns `messages` (the chat log), `batchId` (set
  after a successful upload, gates whether follow-up chat is possible),
  and `llmHistoryRef` (a plain array of `{role, content}` passed back to
  the backend on each follow-up message, giving the model short-term
  conversational context across turns — not persisted, resets on new
  upload).
- **`MessageBubble.jsx`** — renders one message: file attachment
  indicator, source badge (green/grey/red depending on `source`), text,
  and either a full `RecordDetails` list (batch upload) or a single
  `RecordRow` (what-if result from follow-up chat).
- **`RecordDetails.jsx`** — one `<details>` element per record, expandable,
  status chip, explanation with its own source badge, and a flat list of
  every rule/geocode/Maximo issue tagged with which check produced it.
- **`api/client.js`** — two thin `fetch()` wrappers
  (`validateWorkbook`, `sendChatMessage`), both surfacing the backend's
  `detail` error message on non-2xx responses.

Styling is plain CSS custom properties in `App.css` (light/dark aware via
`prefers-color-scheme` and a `data-theme` override), no framework.

---

## 8. Design decisions and why

| Decision | Why |
|---|---|
| **No write path anywhere in the code** | Direct enforcement of the SOW's core principle. `recheck_record` explicitly never persists; there's no function in the codebase that could write to a "real" record even accidentally. |
| **Mock the geocoder and Maximo instead of stubbing with fixed values** | Deterministic-but-controllable (magic tokens) beats both hardcoded-always-pass (proves nothing) and real randomness (breaks repeatable demos). Swappable later behind the same `ValidationComponentResult` contract. |
| **Status decided before AI is ever called** | So the LLM literally cannot influence Green/Amber/Red even if it hallucinated — it receives a finished `RecordValidationResult` and can only narrate or simulate, never mutate. |
| **No AI fallback (as of the latest change)** | Originally: templated text + a regex command parser stood in when Azure wasn't configured, so the POC ran standalone. Reversed on explicit request — silently-degraded output risked being mistaken for real AI output. Now: explicit `"not_configured"`/`"azure_openai_error"` states everywhere, surfaced as UI badges and a dedicated `/api/ai/status` live-connectivity check. |
| **In-memory batch store, not a database** | POC scope — the follow-up chat needs *some* place to remember an uploaded batch across two separate HTTP requests. Explicitly flagged as insufficient for real auditability. |
| **Standalone React chat, not Experience Builder embedding** | Direct scope decision from the person building this: "my part is just the validation agent, like a chatbot" — not a technical limitation, a conscious slice of the full SOW. |
| **Tool-calling loop for follow-up chat, not single-shot Q&A** | This is what makes the chat genuinely "agentic" rather than just another explanation endpoint — the model chooses actions and reasons over live results across turns, matching how the term is used in the current sense (see chat history around 2026-08-23 for the fuller "is it agentic" discussion). |

---

## 9. Notable bugs found during development (and why they matter)

Documented here because they reveal real edge cases in the design, not
just typos:

1. **Enum name vs. value mismatch in the Rule Validator.** `RULE_MATRIX`
   was keyed by `AddressCombination.name` (e.g. `"URBAN_STREET"`) but the
   validator looked it up by `.value` (e.g. `"UrbanStreet"`) — every
   lookup silently missed, so every record came back RED with a useless
   "no rule set defined" error. Caught by running the test suite, not by
   reading the code.
2. **Pydantic enum round-trip bug.** `model_dump()` → reconstruct broke
   `addressType` validation because `AddressType(str, Enum)` isn't
   `enum.StrEnum`, so `str(AddressType.CIVIC)` returns `"AddressType.CIVIC"`,
   not `"Civic"`. This silently broke every `recheck_record` what-if call
   until the validator was made enum-instance-aware.
3. **Word-order bug in the (now-removed) fallback chat parser.**
   `"why is row 2 red?"` matched the "list all RED rows" branch before the
   "specific row" branch, because it checked for the word "red" first —
   dumped every red row instead of answering about row 2 specifically.
4. **Chat summary showed the status header, not the reason.** The first
   line of a multi-line explanation was just `"Row 2 is RED."` — the
   actual error was on a later line that got truncated when the chat
   formatter took only the first line. Fixed by pulling the real error
   message directly from the component result instead of parsing
   `aiExplanation` text.
5. **Silently-dropped issues without a `fieldName`.** `suggestedCorrection`
   was built by filtering `if issue.fieldName`, which dropped geocoding-
   level warnings (they don't tie to one field) — a record could have a
   real warning but an empty (falsy) `suggestedCorrection`. Fixed with a
   `general_N` fallback key.

The throughline: every one of these was caught by actually running the
code against live data (pytest + curl against a running server), not by
reading it — which is why §6's request-flow traces and the test suite in
`backend/tests/` matter as much as the module descriptions above.

---

## 10. What's NOT built (vs. the full SOW)

See README's "Known gaps" for the short version. In architectural terms:

- **Capability 6 (Post-update Reconciliation)** has no code at all — it
  needs real GIS/Maximo read access to mean anything, which this POC
  doesn't have.
- **No Experience Builder integration, no Service Point search/map
  interface** — the SOW's actual delivery surface. This project's chat UI
  is a substitute interface for the validation engine, not the SOW's
  integration target.
- **No auth** on the FastAPI backend — irrelevant while everything is
  synthetic, would be required before touching real ATCO data (the SOW
  explicitly calls out "existing authentication, authorization" must
  remain applicable).
- **No real audit trail** — `batch_store` is in-memory and ephemeral.

---

## 11. Configuration reference

| Variable | Where | Purpose |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | `backend/.env` | Azure OpenAI resource URL |
| `AZURE_OPENAI_API_KEY` | `backend/.env` | Azure OpenAI key |
| `AZURE_OPENAI_DEPLOYMENT` | `backend/.env` | Deployment/model name |
| `AZURE_OPENAI_API_VERSION` | `backend/.env` | Defaults to `2024-02-15-preview` |
| `CORS_ORIGINS` | `backend/.env` | Comma-separated allowed origins; defaults to `http://localhost:5173` |
| `VITE_API_BASE_URL` | `frontend/.env` | Where the frontend sends API calls; defaults to `http://localhost:8000` |

All read once at process startup (`config.py` calls `load_dotenv()` at
import time) — editing `.env` requires restarting the affected server.
