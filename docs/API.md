# API Reference

Base path: `/api`

## Data model highlights

- `state.round` is a display-oriented round indicator.
- `state.round_number` is internal move count (not directly returned).
- One full round consists of **2 moves**: Pro then Con.
- `final_pro_pct` and `final_con_pct` are derived from belief in `[0, 1]`.

---

## `POST /api/start`

Start and run a full debate.

### Request body

```json
{
  "topic": "Should remote work be permanent?",
  "max_rounds": 6
}
```

### Validation rules

- `topic` is required and must be non-empty after trim.
- `max_rounds` is clamped to range `[4, 6]`.

### Response (200)

```json
{
  "state": {
    "topic": "Should remote work be permanent?",
    "round": 6,
    "belief": 0.57,
    "pro_claims": ["..."],
    "con_claims": ["..."],
    "history": [
      {
        "side": "pro",
        "argument": {
          "claim": "...",
          "premises": ["..."],
          "inference": "...",
          "attack_target": 0,
          "strength": 0.68,
          "reasoning_type": "tradeoff"
        },
        "belief_after": 0.55
      }
    ],
    "winner": "pro",
    "turning_point_round": 3,
    "max_rounds": 6
  },
  "summary": {
    "topic": "Should remote work be permanent?",
    "winner": "pro",
    "final_belief": 0.57,
    "final_pro_pct": 57.0,
    "final_con_pct": 43.0,
    "turning_point_round": 3,
    "total_rounds": 12
  },
  "pruning_logs": [
    {
      "side": "pro",
      "round": 1,
      "pruning_log": [
        {
          "depth": 3,
          "side": "pro",
          "action_description": "...",
          "cut_type": "beta",
          "value": 0.61,
          "alpha": 0.61,
          "beta": 0.58
        }
      ]
    }
  ],
  "facts_from_api": true
}
```

### Errors

- `400`: `{ "error": "topic is required" }`

---

## `GET /api/state`

Get current in-memory debate state.

### Response

- If no debate has run yet:

```json
{ "state": null, "summary": null }
```

- Otherwise:

```json
{ "state": { ... }, "summary": { ... } }
```

---

## `GET /api/summary`

Get current summary from latest debate.

### Response (200)

```json
{
  "topic": "...",
  "winner": "pro",
  "final_belief": 0.57,
  "final_pro_pct": 57.0,
  "final_con_pct": 43.0,
  "turning_point_round": 3,
  "total_rounds": 12
}
```

### Errors

- `404`: `{ "error": "no debate run yet" }`

---

## `POST /api/summary`

Get summary with audience override.

### Request body

```json
{ "override_audience": 0.5 }
```

- `override_audience` is clamped to `[0, 1]`.
- `winner` is recomputed from override belief (`pro`, `con`, or `tie`).

### Response

Same schema as `GET /api/summary`, with overridden percentages and winner.

---

## cURL examples

### Start debate

```bash
curl -X POST http://127.0.0.1:5000/api/start \
  -H "Content-Type: application/json" \
  -d '{"topic":"Universal basic income","max_rounds":6}'
```

### Fetch state

```bash
curl http://127.0.0.1:5000/api/state
```

### Override summary

```bash
curl -X POST http://127.0.0.1:5000/api/summary \
  -H "Content-Type: application/json" \
  -d '{"override_audience":1}'
```

