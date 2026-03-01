# ⚔️ DebateAI

An intelligent debate simulation platform where AI agents argue opposing sides of any topic using **adversarial search**, **minimax reasoning**, and **probabilistic belief modelling**. Features a real-time streaming UI, Man vs. Machine interactive mode, and persistent PostgreSQL storage.

---

## ✨ Features

- **AI vs. AI Debates** — Watch two minimax agents argue any topic to completion
- **Man vs. Machine Mode** — Play as Pro or Con and debate against the AI in real-time
- **Probabilistic Belief Meter** — Live spring-animated belief graph showing who's winning each round
- **Streaming SSE** — Typing animations stream each argument word-by-word, round-by-round
- **Multiple Audience Personas** — Skeptic, Credulous, Balanced, or Pro-leaning audiences that change how arguments land
- **Persistent Storage** — All debates saved to PostgreSQL via SQLAlchemy + asyncpg
- **Live API Facts** — Optional Groq LLM integration to pull real-world facts for argument seeding
- **Summary & Download** — Full debate summary card with audience override and PNG export

---

## 🗂️ Project Structure

```
DEBATEAI/
├── backend/               # FastAPI Python backend
│   ├── api/
│   │   ├── index.py       # Vercel serverless entrypoint / FastAPI app factory
│   │   └── routes.py      # All API route handlers
│   ├── domain/            # Pure business logic (no I/O)
│   │   ├── belief.py      # BeliefModel — Bayesian argument scoring
│   │   ├── minimax.py     # MinimaxAgent — adversarial argument search
│   │   ├── reasoning.py   # ArgumentGenerator — claim/argument generation
│   │   └── state.py       # DebateState, Argument, Side, Persona datatypes
│   ├── infra/             # Infrastructure (DB, external APIs)
│   │   ├── database.py    # SQLAlchemy async engine + session factory
│   │   ├── models.py      # ORM models: DebateRecord, RoundRecordModel
│   │   └── groq_client.py # Groq LLM API client for fact seeding
│   ├── services/
│   │   └── debate_service.py # Orchestration: initialize, run, stream debates
│   ├── alembic/           # Database migrations
│   ├── tests/
│   │   └── test_engine.py
│   ├── requirements.txt
│   └── vercel.json
│
└── frontend/              # React + TypeScript + Vite frontend
    ├── src/
    │   ├── components/
    │   │   ├── AgentPanel.tsx    # Per-side argument card with typing animation
    │   │   ├── BeliefMeter.tsx   # Animated spring-fill belief bar
    │   │   ├── DebateView.tsx    # Progressive round-by-round debate layout
    │   │   ├── SummaryCard.tsx   # Post-debate summary, override, download
    │   │   └── TopicInput.tsx    # Topic entry and game mode configuration
    │   ├── api.ts          # Typed API client (fetch + SSE)
    │   ├── App.tsx         # Root state machine and layout
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
pip install -r requirements.txt

# Copy and fill your environment variables
# Set DATABASE_URL and optionally GROQ_API_KEY

# Run migrations
alembic upgrade head

# Start the dev server (from the project root)
uvicorn backend.api.index:app --reload --port 5000
```

### Frontend

```bash
cd frontend
npm install

# Set VITE_API_BASE_URL in .env.local if backend is on a different port/host
npm run dev
```

---

## 🌐 Deployment (Vercel)

This project is deployed as **two separate Vercel projects** from the same GitHub repository.

### Backend Project
- **Root Directory:** `backend`
- **Environment Variables:**
  - `DATABASE_URL` — PostgreSQL connection string (e.g. from Neon)
  - `GROQ_API_KEY` — Optional, for live fact seeding

### Frontend Project
- **Root Directory:** `frontend`
- **Framework Preset:** Vite
- **Environment Variables:**
  - `VITE_API_BASE_URL` — URL of your deployed backend (without trailing `/`)

> ⚠️ After adding `VITE_API_BASE_URL` to your frontend project, you **must redeploy** (not just save) since Vite bakes env vars into the bundle at build time.

---

## 🔑 Environment Variables

| Variable | Where | Description |
|---|---|---|
| `DATABASE_URL` | Backend | PostgreSQL DSN. `postgresql://...` is auto-converted to `asyncpg` format |
| `GROQ_API_KEY` | Backend | Groq API key for LLM fact seeding (optional) |
| `VITE_API_BASE_URL` | Frontend | Full base URL of your deployed backend |

---

## 🤖 How It Works

1. **Topic Input** — User enters a topic and selects audience persona + play mode
2. **`POST /api/start`** — Backend initializes a debate record in PostgreSQL, generates seed claims (optionally via Groq), and returns the empty initial state + debate ID
3. **`GET /api/debate/{id}/stream_turn`** — Frontend opens an SSE stream. The backend runs one minimax turn, streams word-by-word typing events, commits the result to the database, and signals `turn_complete` or `waiting_for_user`
4. **Frontend State Machine** — After each `turn_complete`, the frontend waits 1.2 seconds then requests the next turn, creating a natural reading pace
5. **`POST /api/debate/{id}/move`** — When playing as Pro or Con, the user submits their argument, which is parsed and committed to the database before the AI takes its next turn
6. **`GET /api/summary/{id}`** — Returns the final winner, belief percentages, and turning point round

---

## 💻 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Framer Motion, Tailwind CSS |
| Backend | FastAPI, Python 3.10, Uvicorn |
| Database | PostgreSQL, SQLAlchemy (async), asyncpg, Alembic |
| AI / Reasoning | Custom Minimax + Bayesian belief model |
| LLM (optional) | Groq API (`llama-3.1-8b-instant`) |
| Deployment | Vercel (two projects) |
