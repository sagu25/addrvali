# Demo Readiness & Anticipated Q&A

Is this ready to show? **Yes — as a working first checkpoint of the
validation engine, not as a finished deliverable.** This document says
plainly what's solid, what's missing, and prepares answers for the
questions most likely to come up when you present it.

---

## 1. Is this good enough to show as a start?

**Yes, with the right framing.** What makes it presentable:

- It **runs end-to-end on real logic**, not a mockup or slides — upload a
  batch, get real Green/Amber/Red results, ask follow-up questions, watch
  a what-if simulation re-run the actual pipeline live.
- The **hardest part is real**: the rule-matrix validation (capability 1)
  is genuine deterministic logic against the transcribed ESRI table, not
  a placeholder.
- The **core guardrail is provably enforced**, not just claimed: there is
  no write function anywhere in the codebase. "Explains, never decides"
  is structural, not a policy statement.
- It's **agentic in the real sense** once Azure OpenAI is connected — a
  tool-calling loop that reasons over live results, not a scripted demo.

**The framing that keeps this honest**: present it as *"the validation
core of the Agent, working end-to-end on synthetic data — here's exactly
what's real, what's simulated pending real ATCO access, and what's not
built yet."* That framing survives scrutiny. Presenting it as "the
Address Validation Agent, done" does not — see §2.

---

## 2. What's missing (be ready to say this before someone asks)

### Not built at all
- **Post-update Reconciliation** — the 6th capability. Zero code. Needs
  real GIS/Maximo read access to be meaningful, which this POC doesn't have.
- **Service Point search** (by Distributor Site ID / Service Point Key /
  ObjectID / map click) — the POC only accepts batch Excel upload, no
  lookup-by-ID or map interface.
- **ExB (Experience Builder) embedding** — this is a standalone React chat,
  not a layer inside ATCO's existing ArcGIS app, which is where the
  concept note places it.
- **Real GIS read** — no pulling of current Service Point/address context
  before validating; the POC only validates what's in the uploaded file.
- **Authentication** — the API has none. Irrelevant while synthetic, but
  the SOW requires "existing authentication, authorization" to remain
  applicable once this touches real data.
- **Single-record validation without a file** — SOW says "single and
  batch"; only batch (via Excel) is built.

### Built, but simulated (not connected to the real thing)
- **Geocoding Analyzer** — mocked. Deterministic (token-driven), not a
  real ATCO geocoder call.
- **Pre-dispatch Check** — mocked. Synthetic Maximo linking-field schema,
  not the real Maximo REST contract.

### Built, but not production-grade
- **Audit trail** — batch results live in memory and vanish on server
  restart. Fine for a demo, not real auditability.
- **Rule matrix** — transcribed from a phone photo of the ESRI table. Two
  known gaps: rows 30–31 weren't visible in the source image, and a
  footnote about a conditional rule on the Rural Street combination isn't
  encoded. **Needs sign-off from whoever owns the matrix before it's
  treated as final** — this is the single most important gap to flag,
  since incorrect rules would look convincing but be wrong.

---

## 3. Anticipated questions and prepared answers

### Scope questions

**Q: Is this the whole Address Validation Agent from the SOW?**
No — it's the validation *engine* behind where that Agent would sit. The
SOW places the Agent inside ArcGIS Experience Builder with Service Point
search and real GIS/Maximo connectivity; this POC is a standalone chat
interface over the same validation logic, built to prove the core rules
and decision-making work before investing in the full integration.

**Q: Why isn't it embedded in Experience Builder?**
Scope decision, not a technical blocker — the goal for this phase was
proving the validation logic itself works correctly, which doesn't
require the ExB shell. Embedding is a follow-on integration task.

**Q: What's actually "AI" here versus hand-written logic?**
Only two things touch an LLM: turning an already-decided result into a
plain-language sentence, and answering follow-up chat questions by
calling back into the same deterministic checks. The Green/Amber/Red
decision itself is 100% rule-based code — the AI never decides status,
only narrates it.

### Technical / AI questions

**Q: Is it actually using Azure OpenAI, or is that faked?**
Genuinely real when configured — verifiable via `GET /api/ai/status`,
which makes a live call and reports success/failure, not just whether
credentials exist. There is no fallback: if Azure isn't configured or a
call fails, the app says so explicitly rather than substituting canned
text.

**Q: What happens if Azure OpenAI is down or misconfigured?**
Every response is tagged with its source. If Azure fails, the reply says
"Azure OpenAI call failed: [real error]" and the UI shows a red badge —
it never silently degrades to something that looks like a working answer.

**Q: Is it "agentic," or just a chatbot wrapper around an API?**
It's agentic in the specific sense that matters: the model chooses which
of three tools to call (look up a row, simulate a field change, list rows
by status), reads the real result, and can chain another tool call before
answering — up to 4 rounds. It cannot take an action with side effects;
the only tool that simulates a change explicitly never saves it.

**Q: Could the AI ever approve or submit a record by mistake?**
No — there's no function in the codebase that writes anywhere. The
what-if simulator builds a separate hypothetical copy of a record,
re-validates it, and returns the result; the original stored record is
never touched.

### Data / correctness questions

**Q: Is the rule matrix definitely correct?**
It's a faithful transcription of the ESRI table as photographed, with two
explicitly flagged gaps (two missing rows, one unencoded conditional
rule). **It needs sign-off from the business-rule owner before being
treated as authoritative** — this should be said proactively, not wait to
be asked.

**Q: Does it validate real addresses, or only the demo data?**
Any Excel with an `addressType` column will run through it. The rule
matrix check is fully real regardless of input. The geocoding check is
simulated — a real address won't get a real confidence score, it'll just
default to a high-confidence pass unless deliberately tagged otherwise.

**Q: What data was used to build/test this?**
Entirely synthetic — generated fixtures covering all 6 address
combinations with deliberate pass/warn/fail cases. No real ATCO Service
Point data was used anywhere.

### Roadmap questions

**Q: What's needed to make this production-real?**
In order of effort: (1) sign off the rule matrix, (2) connect the real
ATCO geocoder and Maximo REST contract behind the existing mock
interfaces (swap, not rewrite), (3) build Post-update Reconciliation
against real GIS/Maximo reads, (4) add the ExB embedding and Service
Point search, (5) replace the in-memory store with real persistence and
add authentication.

**Q: How long would that take?**
Not estimated yet — the mocked-service swaps are the smallest lift since
the interfaces are already shaped to receive them; the ExB embedding and
real GIS/Maximo connectivity are the larger unknowns since they depend on
ATCO's access/credentials being available.

**Q: What would you build next if given more time on this POC alone?**
Post-update Reconciliation (mocked, to complete all 6 capabilities) and
single-record validation without requiring a file upload — both close
gaps against the SOW's own stated requirements and are fully buildable
with synthetic data, no real ATCO access needed.
