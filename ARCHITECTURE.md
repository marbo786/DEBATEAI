# DebateAI: Architecture & Integration Plan

## 1. Overall Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React + Tailwind)                    │
│  Topic Input │ Pro Panel │ Belief Meter │ Con Panel │ Summary    │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                              HTTP (fetch / REST)
                                      │
┌─────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (Python / Flask)                       │
│  /api/start  │  /api/round  │  /api/state  │  /api/summary               │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────┐
│                           CORE ENGINE                                    │
│  DebateState │ ArgumentGenerator │ MinimaxAgent │ BeliefModel │ Summary  │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Single request flow**: Frontend calls `POST /api/start` with topic → backend generates claims, runs 4–6 rounds (or step-by-step), returns full debate state + history. Alternative: `GET /api/next_round` for round-by-round.
- **State**: Backend holds one active debate (topic, rounds, belief history). No DB; in-memory for simplicity.

---

## 2. Project Folder Structure

```
DEBATEAI/
├── ARCHITECTURE.md          # This file
├── README.md
├── backend/
│   ├── requirements.txt
│   ├── app.py               # Flask app, routes
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── state.py         # DebateState, Argument dataclass
│   │   ├── reasoning.py     # Logical reasoning templates
│   │   ├── minimax.py       # Minimax + alpha-beta, eval, pruning log
│   │   ├── belief.py        # Audience belief update
│   │   ├── facts_api.py     # Groq API for pro/con facts (optional)
│   │   └── debate.py        # DebateRunner orchestrator
│   └── run.py
├── frontend/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── api.js           # fetch wrappers
│   │   ├── components/
│   │   │   ├── TopicInput.jsx
│   │   │   ├── AgentPanel.jsx
│   │   │   ├── BeliefMeter.jsx
│   │   │   ├── DebateView.jsx
│   │   │   └── SummaryCard.jsx
│   │   └── index.css
│   └── vite.config.js
└── docs/                    # Optional: pruning log explanation
```

---

## 3. Backend Module Responsibilities

| Module      | Responsibility |
|------------|-----------------|
| `state.py` | `Argument` (claim, premises, attack_target, strength), `DebateState` (topic, pro/con claims, history, belief, round). |
| `reasoning.py` | Template-based argument generation: causal, tradeoff, ethical, risk. Input: side, topic, existing claims → structured argument (premises, inference, claim). |
| `minimax.py` | Minimax with alpha-beta (depth 2–3). State = debate state; actions = choose argument (or pass). Eval = f(strength, counter_strength, belief_impact). Log pruned branches. |
| `belief.py` | `update_belief(current_belief, pro_strength, con_strength)` → new belief in [0,1]. Simple weighted or Bayesian-style update. |
| `debate.py` | `DebateRunner`: init from topic (or optional API-provided claims), run rounds (minimax selects move, opponent counters, belief update), produce history + summary. |
| `facts_api.py` | Optional: call Groq API to get pro/con facts for topic; used by app when `GROQ_API_KEY` is set. |
| `app.py` | Routes: `POST /api/start` (body: `{ topic }`), `GET /api/state`, `GET/POST /api/summary`. Return JSON: state, summary, pruning_logs, facts_from_api. |

---

## 4. Data Contracts (JSON)

**Argument (to frontend):**
```json
{
  "claim": "string",
  "premises": ["string"],
  "inference": "string",
  "attack_target": null | index,
  "strength": 0.0–1.0,
  "reasoning_type": "causal|tradeoff|ethical|risk"
}
```

**Debate state (per round):**
```json
{
  "topic": "string",
  "round": 0–6,
  "belief": 0.0–1.0,
  "pro_claims": ["string"],
  "con_claims": ["string"],
  "history": [
    { "side": "pro"|"con", "argument": { ... }, "belief_after": 0.52 },
    ...
  ],
  "winner": null | "pro" | "con",
  "turning_point_round": 1-based index or null
}
```

**Summary:**
```json
{
  "topic": "string",
  "winner": "pro"|"con",
  "final_belief": 0.0–1.0,
  "final_pro_pct": number,
  "final_con_pct": number,
  "turning_point_round": int,
  "total_rounds": int
}
```

---

## 5. Frontend → Backend Connection

1. **Start debate**: `POST /api/start` with `{ "topic": "..." }`. Backend runs full debate (4–6 rounds), returns `{ state, history, summary }`.
2. **Display**: Frontend stores `state` and `history`; renders round-by-round from `history`; belief meter shows current `belief`.
3. **Summary**: When `state.winner` is set, show `SummaryCard` with topic, winner, final result bar (Pro % / Con %), turning point round. "Download as Image" uses html2canvas on the card div.
4. **Override audience**: User picks "Pro" / "Con" / "Neutral" → frontend can recompute display percentage (e.g. 1, 0, 0.5) and show "If audience were X, result would be Y" without calling backend (or optional lightweight endpoint that returns adjusted summary).

---

## 6. Implementation Order

1. Backend: `state.py` → `reasoning.py` → `belief.py` → `minimax.py` → `debate.py` → `app.py`.
2. Frontend: `api.js` → `TopicInput` + `DebateView` (skeleton) → `AgentPanel` + `BeliefMeter` → `SummaryCard` + download + override.
3. Integration: CORS, run Flask + Vite, test one full debate and screenshot flow.

---

## 7. Minimax & Alpha-Beta (Summary)

- **Players**: Pro (maximizer), Con (minimizer). Alternating moves.
- **State**: Current debate state (round, belief, last arguments).
- **Actions**: Pick one of available arguments (from reasoning layer) or pass.
- **Eval(s)**: Score = w1·(belief_impact) + w2·(argument_strength) − w3·(opponent_counter_strength). Pro maximizes, Con minimizes.
- **Depth**: 2–3 plies. Log each pruned branch (action + beta cut / alpha cut) for demo.

---

## 8. Belief Update (Summary)

- Start: `belief = 0.5`.
- Each round: `delta = k * (pro_strength - con_strength)`, `belief = clamp(belief + delta, 0, 1)`. Or Bayesian-style: treat strength as evidence, update posterior. Keep formula simple and documented.

Facts for debates can come from the optional Groq API (when `GROQ_API_KEY` is set) or from generic templates. The architecture keeps the system clean, modular, and implementable (structured reasoning, explainable).
