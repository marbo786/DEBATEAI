# DebateAI — Architecture Reference

## Overview

DebateAI is organized as a **monorepo** with two independently deployable projects:

- `backend/` — FastAPI Python application (Vercel Serverless Function)
- `frontend/` — React + Vite TypeScript SPA (Vercel Static)

They communicate exclusively over HTTP via a typed REST+SSE API.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                        Browser (User)                      │
│                                                            │
│   TopicInput → App.tsx (State Machine) → DebateView       │
│                         ↕                                  │
│              SSE stream + REST fetch                       │
└────────────────────────────┬─────────────────────────────┘
                             │ HTTPS
                             ▼
┌──────────────────────────────────────────────────────────┐
│               Backend (Vercel Python Serverless)           │
│                                                            │
│   api/index.py (FastAPI app factory)                       │
│       └── api/routes.py (APIRouter /api/*)                 │
│                │                                           │
│       services/debate_service.py                           │
│                │                                           │
│       ┌────────┴────────┐                                  │
│       ▼                 ▼                                  │
│   domain/           infra/                                 │
│   minimax.py        database.py  (asyncpg + NullPool)      │
│   belief.py         models.py   (SQLAlchemy ORM)           │
│   reasoning.py      groq_client.py                         │
│   state.py                                                 │
│                         │                                  │
└─────────────────────────┼──────────────────────────────── ┘
                          │ async SQL (asyncpg)
                          ▼
               ┌─────────────────────┐
               │  PostgreSQL (Neon)   │
               │  tables: debates,    │
               │          rounds      │
               └─────────────────────┘
```

---

## Backend Layer Breakdown

### `api/`
- **`index.py`** — Vercel serverless entrypoint. Creates the FastAPI application, registers CORS middleware, attaches the global exception handler, mounts the router, and instantiates app-level singletons (`DebateService`, `get_facts_from_groq`).
- **`routes.py`** — Defines all HTTP endpoints under the `/api` prefix.

### `services/`
- **`debate_service.py`** — The main orchestration layer. Key methods:
  - `initialize_debate(...)` — Creates a DB record and generates seed claims. Called by `POST /api/start`. Does **not** run any debate rounds.
  - `run_turn_stream(...)` — Streams a single AI turn via SSE. Runs one minimax step, streams word-by-word typing events, commits the result to the database.
  - `get_debate_state(...)` — Fetches and reconstructs a `DebateState` from the database.
  - `summarize(...)` — Derives the final summary dict from a `DebateState`.

### `domain/`
Pure logic with **no I/O dependencies**. Easily unit-tested.

| File | Responsibility |
|---|---|
| `state.py` | Data classes: `DebateState`, `Argument`, `RoundRecord`, `Side`, `Persona` |
| `belief.py` | `BeliefModel` — Bayesian belief update from argument strengths |
| `minimax.py` | `MinimaxAgent` — alpha-beta pruned minimax search over argument candidates |
| `reasoning.py` | `ArgumentGenerator` — generates and ranks argument candidates; parses user text |

### `infra/`
Side-effect bearing code (database, HTTP).

| File | Responsibility |
|---|---|
| `database.py` | Creates the SQLAlchemy async engine. Strips `?sslmode=` params from DSN for asyncpg compatibility. Uses `NullPool` for Vercel serverless (no persistent connections). |
| `models.py` | `DebateRecord` and `RoundRecordModel` ORM models |
| `groq_client.py` | Calls Groq LLM API to seed a debate with real-world pro/con claims |

---

## Frontend Layer Breakdown

### `App.tsx` — State Machine
Central controller managing the entire debate lifecycle:

```
idle → starting → streaming (turn_loop) → waiting_for_user → streaming → ... → done
```

Key design decisions:
- `isTurnInFlightRef` prevents double-triggering the `stream_turn` SSE connection.
- After `turn_complete`, a 1.2-second delay is enforced so users can read each argument before the next fires.
- `isDone` state is decoupled from `streamingState` so the `SummaryCard` only appears after a clean `done` event.

### `api.ts` — Typed HTTP Client
- `startDebate()` — `POST /api/start`
- `streamDebateTurn()` — Opens `EventSource` to `GET /api/debate/{id}/stream_turn`
- `submitDebateMove()` — `POST /api/debate/{id}/move`
- `getSummary()` — `GET|POST /api/summary/{id}`
- Falls back through `VITE_API_BASE_URL → /api` with graceful `TypeError` logging.

### Components

| Component | Role |
|---|---|
| `TopicInput.tsx` | Debate setup: topic text input, audience persona tiles, play mode tiles, start button |
| `DebateView.tsx` | Renders completed rounds as stagger-animated cards + live typing round |
| `AgentPanel.tsx` | Per-side argument card with typing cursor, animated strength bar, collapsible reasoning |
| `BeliefMeter.tsx` | Spring-animated dual-fill bar with Pro/Con leading indicator |
| `SummaryCard.tsx` | Final result card with stat tiles, audience override, and PNG download |

---

## Database Schema

### `debates`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Auto-generated |
| `topic` | String | Debate topic text |
| `persona` | String | Audience persona name |
| `user_side` | String | `'auto'`, `'pro'`, or `'con'` |
| `max_rounds` | Integer | Capped at 4–6 |
| `status` | String | `'running'`, `'completed'` |
| `belief` | Float | Current belief value (0–1) |
| `pro_claims` | JSONB | Seed pro claims list |
| `con_claims` | JSONB | Seed con claims list |
| `winner` | String | `'pro'`, `'con'`, or `'tie'` |
| `created_at` | Timestamp | |

### `rounds`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `debate_id` | UUID FK | References `debates.id` |
| `round_number` | Integer | 1-indexed |
| `side` | String | `'pro'` or `'con'` |
| `claim` | Text | Main argument claim |
| `premises` | JSONB | Supporting premises list |
| `inference` | Text | Logical inference chain |
| `strength` | Float | Argument strength (0–1) |
| `reasoning_type` | String | e.g. `'deductive'` |
| `belief_after` | Float | Belief after this round |
| `is_user_move` | Boolean | True if submitted by human player |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/api/start` | Initialize debate, return empty state + debate_id |
| `GET` | `/api/debate/{id}/stream_turn` | SSE stream for one AI turn |
| `POST` | `/api/debate/{id}/move` | Submit a human player argument |
| `GET` | `/api/state/{id}` | Fetch full current debate state |
| `GET/POST` | `/api/summary/{id}` | Get summary, optionally with audience override |

---

## SSE Event Protocol

The `stream_turn` endpoint emits the following `data:` events:

| Event type | Payload | Meaning |
|---|---|---|
| `typing` | `{side, chunk}` | One word of the argument being typed |
| `move` | `{state}` | AI argument committed, full state snapshot |
| `turn_complete` | `{state}` | Turn done, AI is not the next player |
| `waiting_for_user` | `{state}` | It's the human player's turn |
| `done` | `{state, summary}` | Debate finished, final results |
