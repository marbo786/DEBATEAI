<div align="center">

# ⚔️ DebateAI

### Multi-Agent Debate Simulation Platform

**AI agents argue opposing sides of any topic using adversarial search, probabilistic belief modelling, and LLM-driven argument generation**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React_18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com)

🚀 **[Try it Live →](https://debateai-green.vercel.app)**

</div>

---

## 🧠 What Is DebateAI?

DebateAI is an intelligent debate simulation platform with two modes:

- **AI vs. AI** — Watch two minimax agents argue any topic to completion
- **Man vs. Machine** — Play as Pro or Con and debate the AI in real-time

Every argument is scored by a Bayesian belief model, visualised live on an animated belief trajectory chart, and powered (optionally) by Groq's `llama-3.1-8b-instant` LLM for semantically rich, context-aware arguments.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **Minimax Search** | Depth-3 adversarial search with momentum, rebuttal, and diversity heuristics |
| 📊 **Live Belief Meter** | Spring-animated bar showing audience belief shift after every move |
| 📈 **Belief Trajectory Chart** | Animated SVG line chart plotting audience belief round by round |
| 🔄 **Turning Point Detection** | Identifies the round with the largest net belief shift |
| 🎭 **Audience Personas** | Skeptic, Credulous, Balanced, or Pro-leaning — changes how arguments land |
| 💬 **User Move Feedback** | Shows extracted claim, animated strength bar, and reasoning type badge |
| 📡 **Streaming SSE** | Word-by-word typing animations streamed via Server-Sent Events |
| 🔁 **Re-score for Audience** | Replay any debate from a different audience prior belief |
| 💾 **Persistent Storage** | All debates and rounds saved to PostgreSQL via SQLAlchemy + asyncpg |
| 📥 **Summary & Download** | Full debate summary card with PNG export |
| 📱 **Mobile-Optimised** | Responsive layout across all breakpoints; iOS tap-zoom prevention |

---

## 🏗️ Architecture

```
User (Browser)
     │
     ▼
┌─────────────────────────────────┐
│  React + TypeScript Frontend    │  ← Vite, Framer Motion, Tailwind CSS
│  (Vercel — frontend project)    │
└──────────────┬──────────────────┘
               │  REST + SSE (Server-Sent Events)
               ▼
┌─────────────────────────────────┐
│  FastAPI Backend                │  ← Uvicorn, async Python
│  (Vercel — backend project)     │
│                                 │
│  ┌─────────────┐                │
│  │  Minimax    │ ← depth-3 search with heuristics
│  │  Agent      │
│  └──────┬──────┘
│         │ candidates
│  ┌──────▼──────┐
│  │  Groq LLM   │ ← llama-3.1-8b-instant (optional)
│  │  + Templates│
│  └──────┬──────┘
│         │ scored arguments
│  ┌──────▼──────┐
│  │  Bayesian   │ ← belief = belief + sensitivity × (strength − 0.5) × side
│  │  Belief     │
│  │  Model      │
│  └──────┬──────┘
│         │
└─────────┼───────────────────────┘
          │
          ▼
┌─────────────────┐
│   PostgreSQL    │  ← DebateRecord + RoundRecordModel (Alembic migrations)
└─────────────────┘
```

---

## 🔄 Turn Flow

```
1. POST /api/start
   └─ Initialise debate record in DB
   └─ Generate seed claims (Groq or templates)
   └─ Return debate ID + empty state

2. GET /api/debate/{id}/stream_turn   [SSE stream]
   └─ Generate LLM + template argument candidates
   └─ Minimax (depth 3) picks the best argument
   └─ Stream word-by-word typing events to frontend
   └─ Commit move to DB → signal turn_complete / waiting_for_user

3. POST /api/debate/{id}/move         [user turn only]
   └─ Groq / heuristics parse user argument (claim + strength)
   └─ Commit to DB → AI takes next turn

4. POST /api/summary/{id}
   └─ Return winner, trajectory, turning point
   └─ Optional: re-score with override_audience
```

---

## 📁 Project Structure

```
DEBATEAI/
├── backend/
│   ├── api/
│   │   ├── index.py            # Vercel serverless entrypoint / FastAPI app factory
│   │   └── routes.py           # Route handlers: start, stream_turn, move, summary
│   ├── domain/                 # Pure business logic (zero I/O)
│   │   ├── belief.py           # BeliefModel — Bayesian argument scoring
│   │   ├── minimax.py          # MinimaxAgent — adversarial search + heuristics
│   │   ├── reasoning.py        # ArgumentGenerator — claim generation + user parsing
│   │   └── state.py            # DebateState, Argument, Side, Persona datatypes
│   ├── infra/
│   │   ├── database.py         # SQLAlchemy async engine + session factory
│   │   ├── models.py           # ORM: DebateRecord, RoundRecordModel
│   │   └── groq_client.py      # Groq LLM client: fact seeding + argument generation
│   ├── services/
│   │   └── debate_service.py   # Orchestration: initialize, stream, summarize
│   ├── alembic/                # Database migrations
│   ├── tests/
│   │   └── test_engine.py      # 32 unit tests
│   ├── requirements.txt
│   └── vercel.json
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── AgentPanel.tsx   # Argument card with typing animation + strength bar
    │   │   ├── BeliefChart.tsx  # Animated SVG belief trajectory chart
    │   │   ├── BeliefMeter.tsx  # Spring-animated belief bar
    │   │   ├── DebateView.tsx   # Round-by-round layout + progress dots
    │   │   ├── SummaryCard.tsx  # Post-debate summary + PNG download
    │   │   └── TopicInput.tsx   # Topic entry + game mode config
    │   ├── api.ts               # Typed API client (fetch + SSE)
    │   ├── types.ts             # Shared TypeScript interfaces
    │   ├── App.tsx              # Root state machine + streaming logic
    │   └── index.css            # Global styles and design tokens
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
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt

# Run DB migrations
alembic upgrade head

# Start dev server (from project root)
uvicorn backend.api.index:app --reload --port 5000
```

### Frontend

```bash
cd frontend
npm install

# Optional: set backend URL
echo "VITE_API_BASE_URL=http://localhost:5000" > .env.local

npm run dev
```

---

## 🌐 Deployment (Vercel)

Deployed as **two separate Vercel projects** from the same GitHub repository.

### Backend Project

| Setting | Value |
|---------|-------|
| Root Directory | `backend` |
| `DATABASE_URL` | PostgreSQL connection string (e.g. from Neon) |
| `GROQ_API_KEY` | Groq API key — optional, enables LLM generation |

### Frontend Project

| Setting | Value |
|---------|-------|
| Root Directory | `frontend` |
| Framework Preset | Vite |
| `VITE_API_BASE_URL` | Full URL of your deployed backend (no trailing `/`) |

> ⚠️ After adding `VITE_API_BASE_URL`, **redeploy** (don't just save) — Vite bakes env vars into the bundle at build time.

---

## 🔑 Environment Variables

| Variable | Where | Description |
|----------|-------|-------------|
| `DATABASE_URL` | Backend | PostgreSQL DSN — `postgresql://...` auto-converted to `asyncpg` format |
| `GROQ_API_KEY` | Backend | Groq API key for LLM argument generation (optional, graceful fallback) |
| `VITE_API_BASE_URL` | Frontend | Full base URL of your deployed backend |

---

## 🧪 Testing

```bash
# Backend — 32 unit tests
python -m pytest backend/tests/test_engine.py -v

# Frontend — TypeScript type check
cd frontend && npx tsc --noEmit
```

Tests cover: belief model, minimax heuristics, argument deduplication (Jaccard similarity), turning point calculation, and debate state serialisation.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| 🖥️ Frontend | React 18, TypeScript, Vite, Framer Motion, Tailwind CSS |
| ⚡ Backend | FastAPI, Python 3.10, Uvicorn |
| 🗄️ Database | PostgreSQL, SQLAlchemy (async), asyncpg, Alembic |
| 🤖 AI / Reasoning | Custom Minimax + Bayesian belief model + Jaccard deduplication |
| 🧠 LLM | Groq API (`llama-3.1-8b-instant`) — optional, graceful fallback |
| 🚀 Deployment | Vercel (two projects) |

---

## 👤 Author

**Mohsin Saeed**
📧 [marboo786@gmail.com](mailto:marboo786@gmail.com)
🐙 [github.com/marbo786](https://github.com/marbo786)

---

<div align="center">

Built with ❤️ using FastAPI, React & Groq

⭐ Star this repo if you found it interesting!

</div>
