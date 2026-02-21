# DebateAI

DebateAI is a full-stack AI debate simulator where two autonomous agents (Pro and Con) argue a user-provided topic.

The project demonstrates core AI concepts in an explainable way:
- **adversarial search** (minimax + alpha-beta pruning),
- **structured argument generation** (claim + premises + inference),
- **probabilistic belief updates** for audience stance,
- optional **external factual grounding** through the Groq API.

---

## Table of Contents

- [What this project does](#what-this-project-does)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [How the debate engine works](#how-the-debate-engine-works)
- [Frontend behavior](#frontend-behavior)
- [Development workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [Additional docs](#additional-docs)

---

## What this project does

1. Accepts a debate topic from the UI.
2. Optionally fetches pro/con factual claims from Groq (if `GROQ_API_KEY` is set).
3. Runs a complete debate in the backend for 4 to 6 rounds.
4. Produces a structured history of arguments and belief changes.
5. Returns a summary (winner, percentages, turning point).
6. Lets users override audience stance in the UI and export a summary card image.

---

## Tech stack

### Backend
- Python 3.10+
- Flask + Flask-CORS
- `httpx` for optional Groq API calls

### Frontend
- React (Vite)
- Tailwind CSS
- `html2canvas` for summary image export

---

## Project structure

```text
DEBATEAI/
├── backend/
│   ├── app.py                 # Flask routes and request handling
│   ├── run.py                 # server entrypoint
│   ├── requirements.txt
│   └── engine/
│       ├── state.py           # dataclasses and state serialization
│       ├── reasoning.py       # argument generation logic
│       ├── belief.py          # audience belief model
│       ├── minimax.py         # minimax + alpha-beta pruning
│       ├── debate.py          # orchestration of full debate runs
│       └── facts_api.py       # optional Groq fact retrieval
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js             # backend API client wrappers
│   │   └── components/
│   └── package.json
├── docs/
│   ├── API.md
│   ├── ENGINE.md
│   ├── FRONTEND.md
│   └── DEPLOYMENT.md
├── ARCHITECTURE.md
└── README.md
```

---

## Quick start

## 1) Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows PowerShell/CMD
pip install -r requirements.txt
python run.py
```

Backend default URL: `http://127.0.0.1:5000`

## 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default URL: `http://localhost:5173`

Vite proxies `/api/*` to backend during development.

---

## Configuration

### Optional: Groq API integration

Set `GROQ_API_KEY` before starting backend:

```bash
export GROQ_API_KEY="your-key-here"     # macOS/Linux
# set GROQ_API_KEY=your-key-here         # Windows cmd
# $env:GROQ_API_KEY="your-key-here"     # Windows PowerShell
```

If unset or if API fails, DebateAI gracefully falls back to template claims.

---

## API reference

Detailed API documentation: **[`docs/API.md`](docs/API.md)**.

Available endpoints:
- `POST /api/start`
- `GET /api/state`
- `GET|POST /api/summary`

---

## How the debate engine works

Detailed engine docs: **[`docs/ENGINE.md`](docs/ENGINE.md)**.

At a high level:
- `ArgumentGenerator` creates candidate pro/con arguments.
- `MinimaxAgent` chooses the strongest move for each side.
- `BeliefModel` updates audience belief after each move.
- `DebateRunner` executes alternating turns and computes winner + turning point.

---

## Frontend behavior

Detailed UI docs: **[`docs/FRONTEND.md`](docs/FRONTEND.md)**.

The frontend:
- starts debates,
- visualizes round-by-round arguments,
- displays belief and winner,
- allows audience override,
- exports summary card image.

---

## Development workflow

### Validate backend syntax
```bash
python -m compileall backend/app.py backend/engine
```

### Build frontend
```bash
cd frontend && npm run build
```

---

## Troubleshooting

- **`topic is required` (400)**: Ensure non-empty topic in `/api/start` payload.
- **No API facts badge in UI**: Verify `GROQ_API_KEY` is set and valid.
- **CORS/proxy issues locally**: Ensure backend is running on port `5000` and frontend on `5173`.
- **summary endpoint returns 404**: Run `/api/start` first (state is in-memory).

---

## Additional docs

- [API Reference](docs/API.md)
- [Engine Deep Dive](docs/ENGINE.md)
- [Frontend Guide](docs/FRONTEND.md)
- [Deployment & Operations](docs/DEPLOYMENT.md)
- [Architecture Notes](ARCHITECTURE.md)

