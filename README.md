# DebateAI: Watch Algorithms Argue

An AI Political Debate Simulator where two autonomous agents debate a user-provided topic using **adversarial search** (Minimax + Alpha-Beta), **logical reasoning**, **knowledge representation**, and **probabilistic audience belief**.

## Run locally

### Backend (Python)

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python run.py
```

API runs at **http://127.0.0.1:5000**.

### Frontend (React + Vite + Tailwind)

```bash
cd frontend
npm install
npm run dev
```

App runs at **http://localhost:5173**. It proxies `/api` to the backend.

1. Enter a debate topic and click **Start Debate**.
2. View Pro vs Con panels and the audience belief meter.
3. After the debate, use the summary card: **Download as image**, and **Override audience** (Pro / Neutral / Con) to see recalculated percentages.

## Architecture

- **Backend** (`backend/`): Flask API; engine in `engine/` (state, reasoning, belief, minimax, debate).
- **Frontend** (`frontend/`): React + Tailwind; components for topic input, agent panels, belief meter, summary card.

See **ARCHITECTURE.md** for data contracts, module roles, and integration plan.

## Concepts demonstrated

- **Adversarial reasoning**: Minimax with Alpha-Beta pruning (depth 2–3); Pro maximizes audience belief, Con minimizes.
- **Logical inference**: Template-based causal, tradeoff, ethical, and risk reasoning; each argument has premises and inference.
- **Probabilistic belief**: Audience belief in [0, 1] updated each round from argument strengths; simple weighted update.
- **Decision theory**: Agents choose moves to maximize/minimize expected belief impact.

Single reasoning system; no personality variants. Kept clear and implementable for an introductory AI course.

## Real-world facts (Groq API)

For a more realistic debate, the app can fetch **pro/con facts** for any topic from the **Groq API** (free tier).

1. Get a free API key at [console.groq.com](https://console.groq.com).
2. Set it in your environment before starting the backend:
   - Windows (PowerShell): `$env:GROQ_API_KEY="your-key-here"`
   - Windows (cmd): `set GROQ_API_KEY=your-key-here`
   - macOS/Linux: `export GROQ_API_KEY=your-key-here`
3. Start a debate: if the key is set, the backend calls Groq once to get factual pro and con claims for your topic. If the key is missing or the API fails, the app falls back to generic template claims.
4. When API facts are used, the UI shows an **"Using API facts"** badge next to the debate topic.
