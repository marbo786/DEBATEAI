# ⚔️ DebateAI

An intelligent debate simulation platform where AI agents argue opposing sides of any topic using **adversarial search**, **minimax reasoning**, and **probabilistic belief modelling**. Features real-time streaming, LLM-powered argument generation, live belief trajectory visualisation, and Man vs. Machine interactive mode.

---

## ✨ Features

- **AI vs. AI Debates** — Watch two minimax agents argue any topic to completion
- **Man vs. Machine Mode** — Play as Pro or Con and debate the AI in real-time
- **LLM-Powered Arguments** — Groq (`llama-3.1-8b-instant`) generates semantically rich, round-themed arguments; minimax picks the best from LLM + template candidates
- **Probabilistic Belief Meter** — Live spring-animated bar showing who's winning; updates after every move
- **Belief Trajectory Chart** — Animated SVG line chart plotting audience belief round by round with PRO/CON zone labels, winner chips per round, turning point column highlight, and hover tooltips
- **Turning Point Detection** — Identifies the round with the largest net audience belief shift (round-level, not per-move)
- **User Move Feedback** — After submitting an argument, an analysis panel appears showing extracted claim, animated strength bar, and reasoning type badge
- **Round Progress Dots** — Visual stepper between chart and rounds, colour-coded by round winner
- **Streaming SSE** — Word-by-word typing animations streamed via Server-Sent Events
- **Multiple Audience Personas** — Skeptic, Credulous, Balanced, or Pro-leaning audiences that change how arguments land
- **Re-score for Audience** — Replay the debate from a different audience prior belief after it finishes
- **Persistent Storage** — All debates and rounds saved to PostgreSQL via SQLAlchemy + asyncpg
- **Summary & Download** — Full debate summary card with PNG export
- **Mobile-Optimised** — Responsive layout across all breakpoints; iOS tap-zoom prevention

---

## 🗂️ Project Structure

```
DEBATEAI/
├── backend/               # FastAPI Python backend
│   ├── api/
│   │   ├── index.py       # Vercel serverless entrypoint / FastAPI app factory
│   │   └── routes.py      # API route handlers (start, stream_turn, move, summary)
│   ├── domain/            # Pure business logic (no I/O)
│   │   ├── belief.py      # BeliefModel — Bayesian argument scoring
│   │   ├── minimax.py     # MinimaxAgent — adversarial argument search with momentum/rebuttal/diversity heuristics
│   │   ├── reasoning.py   # ArgumentGenerator — claim/argument generation + user argument parsing
│   │   └── state.py       # DebateState, Argument, Side, Persona datatypes
│   ├── infra/             # Infrastructure (DB, external APIs)
│   │   ├── database.py    # SQLAlchemy async engine + session factory
│   │   ├── models.py      # ORM models: DebateRecord, RoundRecordModel
│   │   └── groq_client.py # Groq LLM client: fact seeding + structured argument generation
│   ├── services/
│   │   └── debate_service.py # Orchestration: initialize, stream turns, summarize, turning point
│   ├── alembic/           # Database migrations
│   ├── tests/
│   │   └── test_engine.py # 32 unit tests covering belief model, minimax, deduplication, turning point
│   ├── requirements.txt
│   └── vercel.json
│
└── frontend/              # React + TypeScript + Vite frontend
    ├── src/
    │   ├── components/
    │   │   ├── AgentPanel.tsx    # Per-side argument card with typing animation + strength bar
    │   │   ├── BeliefChart.tsx   # Animated SVG belief trajectory chart
    │   │   ├── BeliefMeter.tsx   # Spring-animated belief bar
    │   │   ├── DebateView.tsx    # Progressive round-by-round layout + round progress dots
    │   │   ├── SummaryCard.tsx   # Post-debate summary, audience override, PNG download
    │   │   └── TopicInput.tsx    # Topic entry and game mode configuration
    │   ├── api.ts          # Typed API client (fetch + SSE)
    │   ├── types.ts        # Shared TypeScript interfaces (single source of truth)
    │   ├── App.tsx         # Root state machine, streaming, user move feedback panel
    │   └── index.css       # Global styles and design tokens
    └── vercel.json
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (local or [Neon.tech](https://neon.tech) cloud)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate     # Windows
# venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

# Set environment variables (see below)
# Run DB migrations
alembic upgrade head

# Start the dev server (from project root)
uvicorn backend.api.index:app --reload --port 5000
```

### Frontend

```bash
cd frontend
npm install

# Optional: set VITE_API_BASE_URL in .env.local if backend is on a different host
npm run dev
```

---

## 🌐 Deployment (Vercel)

Deployed as **two separate Vercel projects** from the same GitHub repository.

### Backend Project
- **Root Directory:** `backend`
- **Environment Variables:**
  - `DATABASE_URL` — PostgreSQL connection string (e.g. from Neon)
  - `GROQ_API_KEY` — Optional; enables LLM fact seeding and argument generation

### Frontend Project
- **Root Directory:** `frontend`
- **Framework Preset:** Vite
- **Environment Variables:**
  - `VITE_API_BASE_URL` — URL of your deployed backend (no trailing `/`)

> ⚠️ After adding `VITE_API_BASE_URL`, **redeploy** (not just save) — Vite bakes env vars into the bundle at build time.

---

## 🔑 Environment Variables

| Variable | Where | Description |
|---|---|---|
| `DATABASE_URL` | Backend | PostgreSQL DSN. `postgresql://...` is auto-converted to `asyncpg` format |
| `GROQ_API_KEY` | Backend | Groq API key for LLM fact seeding + argument generation (optional) |
| `VITE_API_BASE_URL` | Frontend | Full base URL of your deployed backend |

---

## 🤖 How It Works

### Turn Flow
1. **Topic Input** — User selects topic, audience persona, and play mode
2. **`POST /api/start`** — Backend initialises a debate record in PostgreSQL, generates seed claims (optionally via Groq), returns empty state + debate ID
3. **`GET /api/debate/{id}/stream_turn`** — Frontend opens an SSE stream. The backend:
   - Generates LLM candidates via Groq + template candidates from `ArgumentGenerator`
   - Runs Minimax (depth 3) with momentum, rebuttal, and diversity heuristics to pick the best argument
   - Streams word-by-word typing events, then commits the move to the database
   - Signals `turn_complete` or `waiting_for_user`
4. **Frontend State Machine** — After each `turn_complete`, waits 1.2s then requests the next turn
5. **`POST /api/debate/{id}/move`** — User-submitted arguments are parsed by Groq (semantic analysis) or heuristics, then committed before the AI takes its next turn
6. **`POST /api/summary/{id}`** — Returns winner, belief trajectory, turning point round, and re-scores if `override_audience` is provided

### Belief Model
- Each argument has a `strength` score (0–1) from LLM or heuristics
- `new_belief = belief + sensitivity × (strength − 0.5) × side_sign`
- Turning point = the complete debate round with the largest `|belief_end − belief_start|`

---

## 💻 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Framer Motion, Tailwind CSS |
| Backend | FastAPI, Python 3.10, Uvicorn |
| Database | PostgreSQL, SQLAlchemy (async), asyncpg, Alembic |
| AI / Reasoning | Custom Minimax + Bayesian belief model + argument deduplication |
| LLM | Groq API (`llama-3.1-8b-instant`) — optional, graceful fallback |
| Deployment | Vercel (two projects) |

---

## 🧪 Testing

```bash
# Backend — 32 unit tests
python -m pytest backend/tests/test_engine.py -v

# Frontend — TypeScript type check
cd frontend && npx tsc --noEmit
```

Tests cover: belief model, minimax heuristics, argument deduplication (Jaccard similarity), turning point calculation, and debate state serialisation.
