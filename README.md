# Meridian CRM — AI-First HCP Module · *Log Interaction* Screen

An AI-first Customer Relationship Management (CRM) module for pharmaceutical field
representatives. It reimagines the single most repeated task in a rep's day — **logging
an interaction with a Healthcare Professional (HCP)** — around an LLM agent, so notes
become structured, queryable CRM records with zero form-filling friction.

The *Log Interaction* screen puts a **structured form and an AI assistant side by side**, and
they share one record. The rep can capture an interaction three ways — and in every case the
form is what they confirm:

1. **Chat** — the rep briefs the CRM in natural language ("*met Dr. Mehta, discussed Cardizem
   efficacy, positive, shared the brochure*"). A **LangGraph** agent picks a tool (log, edit,
   look up history, fetch HCP details, schedule a follow-up) and the extracted fields are
   **written straight into the form**, highlighted for review.
2. **Voice note** — dictation, gated behind an explicit **consent** step. The transcript runs
   through the same extraction pipeline; the consent answer is stored on the record.
3. **The form itself** — every field is editable by hand, and a hand-edit always beats the AI.

The AI fills; the human confirms. Nothing the agent extracts is beyond the rep's reach.

![Log Interaction screen](docs/screenshot.png)

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | **React 18 + Redux Toolkit + Vite**, Google **Inter** font |
| Backend | **Python + FastAPI** (async) |
| Agent framework | **LangGraph** (`StateGraph`) |
| LLM | **Groq · `llama-3.3-70b-versatile`** (via the OpenAI-compatible endpoint) — see the note below on `gemma2-9b-it` |
| Database | **PostgreSQL** (async SQLAlchemy 2.0 + `asyncpg`) — schema created from the ORM models on startup |

---

## Quick start

### Option A — one command (Docker)

```bash
cp .env.example .env          # then edit LLM_API_KEY with your Groq token
docker compose up --build
# open http://localhost:3000
```

### Option B — local dev (no Docker)

```bash
# 0) Create an empty Postgres database (once)
psql -U postgres -c "CREATE DATABASE crm;"

# 1) Backend
cd backend
python -m venv .venv && . .venv/Scripts/activate    # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set LLM_API_KEY and DATABASE_URL (see below)
uvicorn app.main:app --reload --port 8000

# 2) Frontend  (new terminal)
cd frontend
npm install
npm run dev                    # http://localhost:5173 (proxies /api to :8000)
```

> **Database.** Set `DATABASE_URL` in `backend/.env`:
> `postgresql+asyncpg://postgres:<password>@localhost:5432/crm`. The three tables
> (`hcps`, `interactions`, `follow_ups`) are created from `app/models.py` on startup — there
> is **no hand-written DDL** to keep in sync. `docker compose up` provisions its own Postgres
> and sets this for you.

> **Groq token.** Create one at <https://console.groq.com/keys> and put it in `.env` as
> `LLM_API_KEY`. Without a key the app still runs end-to-end in an **offline fallback**
> (deterministic heuristics stand in for the model) so the flows are demonstrable without
> network access — the header badge shows the model + `offline` until a key is set.

---

## A note on the model: `gemma2-9b-it` has been decommissioned

The brief specifies `gemma2-9b-it`. **Groq has since retired that model** — every request now
fails with:

```
400 model_decommissioned — "The model `gemma2-9b-it` has been decommissioned
and is no longer supported."   https://console.groq.com/docs/deprecations
```

Confirmed against the live `GET /v1/models` endpoint: `gemma2-9b-it` is absent,
`llama-3.3-70b-versatile` is present. So the app runs on **`llama-3.3-70b-versatile`** — the
alternative the brief itself names ("*You may also consider llama-3.3-70b-versatile*").

Two things this exercised, both by design:

- **The model was never hardcoded.** It is `LLM_MODEL_CHAT` / `LLM_MODEL_ROUTER` in `.env`, so
  the swap was a config change with **zero code changes**. If Groq restores gemma2, flip the two
  lines back.
- **The app did not fall over.** Because a failed LLM call degrades to a deterministic heuristic
  extractor instead of raising, the CRM kept logging interactions correctly against a
  decommissioned model — it just did so with dumber extraction. The `400` showed up in the logs,
  not in the rep's face.

The original JSON-mode design still holds: `gemma2` did not reliably support Groq's native
tool-calling, so the router uses `response_format={"type":"json_object"}` and the graph executes
the chosen tool deterministically. That approach is model-agnostic, which is precisely why the
swap was painless.

---

## Architecture

```
 React + Redux + Vite (Inter)          FastAPI (async)                LangGraph agent            Groq
┌───────────────────────────┐  HTTP   ┌──────────────────────┐       ┌────────────────────┐    llama-3.3-70b
│ Log Interaction screen     │ ──────▶ │ /api/v1/interactions │ ────▶ │ StateGraph:         │──▶ (OpenAI SDK →
│  • Structured form   ◀──┐  │        │   POST · GET · PATCH  │       │  load_context       │    Groq endpoint)
│  • AI assistant  ───────┘  │        │ /api/v1/extract (draft)│      │  → router (JSON)    │
│    (fills the form)        │ ◀────── │ /api/v1/chat  (agent) │ ◀──── │  → execute_tool     │
│ HCP sidebar + timeline     │        │ /api/v1/hcps · /health│       │  → responder        │
└───────────────────────────┘        └──────────┬───────────┘       └─────────┬──────────┘
   Redux slices: hcps /                          │ async SQLAlchemy            │
   interactions / chat / draft              PostgreSQL (asyncpg)          5 CRM tools
```

Both the form and the chat funnel into the **same agent tools**, so the AI logic lives in
exactly one place (`backend/app/agent/tools.py`). A form submit calls `log_interaction`
directly; a chat message goes through the full graph.

---

## The LangGraph Agent

### Role

The LangGraph agent is the **reasoning layer** of the CRM. On every rep message it:

1. **`load_context`** — loads the selected HCP's profile and last few interactions from the DB,
   so the agent reasons *with* the relationship, not blind.
2. **`router`** — asks `llama-3.3-70b-versatile` (in JSON mode) which single tool best serves the rep's
   intent, returning `{ "tool": ..., "args": {...} }`.
3. **`execute_tool`** — runs that tool inside a DB transaction.
4. **`responder`** — writes a short, natural confirmation and, where useful, a **next-best-action**
   nudge.

In short, it turns messy field notes into structured, queryable CRM records and keeps the rep
in a fast conversational loop instead of form-filling.

> **Why JSON routing and not native tool-calling?** The design was originally forced by
> `gemma2-9b-it`, which does **not** reliably support Groq's native OpenAI `tools=`
> function-calling parameter. So the agent does **not** use `bind_tools`; the router node uses
> **JSON mode** (`response_format={"type":"json_object"}`) and the graph executes the chosen tool
> deterministically.
>
> That constraint turned out to be a feature. Because routing depends only on JSON mode — which
> every Groq model supports — the agent is **model-agnostic**, and swapping the decommissioned
> gemma2 for `llama-3.3-70b-versatile` needed **zero code changes**: two lines in `.env`.
> `LLM_MODEL_ROUTER` is independently configurable, so the router can run a stronger model than
> the extractor if you want.

The graph is compiled **once** at startup (FastAPI lifespan) and reused for every request.

### The 5 tools

Defined in `backend/app/agent/tools.py`:

#### 1. `log_interaction` *(captures interaction data)*
The core capability. Pipeline:
- **Input**: `hcp_id` + `raw_notes` (a chat message or the form's notes field), plus any
  structured fields the rep set explicitly.
- **LLM summarisation + entity extraction**: `llama-3.3-70b-versatile` (JSON mode) converts the notes into
  a structured record — a concise **summary**, plus extracted **interaction_type**,
  **products_discussed**, **samples_dropped**, **sentiment**, **key_topics**, and a
  **follow_up_needed** flag.
- **Merge**: rep-provided fields override the model's guesses (the human is the source of truth).
- **Persist**: writes an `Interaction` row (`source = 'form' | 'chat'`) and returns it.
- **Robustness**: a heuristic extractor backfills any field the model omits, so a record is always
  well-formed (and the tool still works in offline mode).

This one tool powers **both** UI modes — the form POST and the chat "log a call…" both call it.

#### 2. `edit_interaction` *(modifies logged data)*
- **Structured mode**: the form's *Edit* modal sends an explicit field patch (`PATCH /interactions/{id}`).
- **Natural-language mode**: in chat ("*actually, change the sentiment to positive and note we
  discussed dosing*"), the model is given the current record + the instruction and returns a
  **field-level patch**.
- Every patch is validated against an **allow-list** of editable fields (and enum checks for
  type/sentiment) before being applied; `updated_at` is bumped. If no `interaction_id` is supplied
  in chat, the HCP's most recent interaction is edited — matching the natural "*change that*" flow.

#### 3. `get_interaction_history`
Returns an HCP's recent interactions (newest first) so the rep can ask "*what did we discuss last time?*"
and the agent can ground follow-ups in real history.

#### 4. `get_hcp_details`
Looks up an HCP by id or **fuzzy name** → profile (specialty, institution, tier, preferred products).
Lets the chat resolve "*log a call with Dr. Rao*" to the right record.

#### 5. `schedule_followup`
Creates a `FollowUp` (due date + purpose), optionally linked to an interaction — the basis for a
**next-best-action** the responder can surface.

---

## Data model

`backend/app/models.py` — three tables (JSON columns are portable across Postgres & SQLite):

- **HCP** — `name, specialty, institution, tier (A/B/C), preferred_products[], email, city`
- **Interaction** — `hcp_id, rep_name, interaction_type (call|visit|email|virtual|meeting),
  interaction_date, channel, attendees[], products_discussed[], materials_shared[],
  samples_dropped[], sentiment, key_topics[], topics_discussed, outcomes, follow_up_actions,
  summary, raw_notes, follow_up_needed, consent_obtained, source (form|chat|voice),
  created_at, updated_at`
- **FollowUp** — `hcp_id, interaction_id?, due_date, purpose, status`

`materials_shared` (informational leave-behinds — brochures, reprints, decks) is deliberately
distinct from `samples_dropped` (physical drug samples); the extractor is told never to put an
item in both. `consent_obtained` records whether the HCP agreed to be recorded, so an
interaction captured by voice carries its own audit trail.

Tables are created on startup, and `app/seed.py::_migrate` idempotently `ALTER`s in any column
an older database is missing — so an existing `crm.db` or Postgres volume upgrades in place.

The app ships with **no demo data**. It starts empty — add your own HCPs from the sidebar.

---

## API

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/health` | status + which model / DB is active |
| `GET`  | `/api/v1/hcps` · `/api/v1/hcps/{id}` | HCP directory |
| `GET`  | `/api/v1/interactions?hcp_id=` | list interactions |
| `POST` | `/api/v1/interactions/extract` | **draft only** → structured fields, *nothing persisted* |
| `POST` | `/api/v1/interactions` | **form log** → `log_interaction` (AI-enriched) |
| `PATCH`| `/api/v1/interactions/{id}` | **structured edit** → `edit_interaction` |
| `POST` | `/api/v1/chat` | **conversational** → full LangGraph agent |

`/extract` is what keeps the human in the loop: it turns free text (typed notes or a voice
transcript) into form fields *without touching the database*. The rep reviews the draft and
submits it themselves. When the **chat** logs an interaction the row does get created — so the
form binds to that record's `id` and submitting **PATCHes** it rather than inserting a
duplicate.

Interactive docs at `http://localhost:8000/docs`.

---

## Project layout

```
ai-crm-hcp/
├─ docker-compose.yml          # db + backend + frontend, one command
├─ backend/
│  └─ app/
│     ├─ main.py               # FastAPI app, lifespan builds the agent once
│     ├─ config.py             # pydantic-settings
│     ├─ models.py schemas.py  # ORM + API models
│     ├─ db/session.py         # async SQLAlchemy engine + session_scope()
│     ├─ llm/client.py         # Groq via OpenAI SDK (+ json_chat, offline fallback)
│     ├─ agent/
│     │  ├─ graph.py           # LangGraph StateGraph (load→router→tool→respond)
│     │  ├─ tools.py           # the 5 tools
│     │  ├─ prompts.py state.py
│     └─ api/routes/           # health · hcps · interactions · chat
└─ frontend/
   └─ src/
      ├─ store/                # Redux Toolkit slices: hcps · interactions · chat
      ├─ api/client.js         # single fetch helper
      ├─ components/           # LogInteractionScreen, InteractionForm, ChatPanel,
      │                        # HcpSidebar, InteractionList, EditInteractionModal
      └─ theme.css             # Inter-based design system
```

---

## Try it

**Form mode** — select an HCP, type: *"Quick visit with Dr. Mehta, discussed Cardizem dosing,
left 5 samples, very positive, wants a follow-up next month"* → the record comes back with an
auto **summary**, `type=visit`, `sentiment=positive`, `samples=[Cardizem x5]`, `follow_up_needed=true`.

**Chat mode** — switch to the *Conversational* tab:
- *"log a virtual visit with Dr. Rao about the new Jardiance label, neutral tone"* → agent runs
  `log_interaction`.
- *"actually change the sentiment to positive"* → agent runs `edit_interaction` on the last record.
- *"what did we discuss recently?"* → agent runs `get_interaction_history`.
