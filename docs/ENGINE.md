# Debate Engine Deep Dive

This document explains how the backend engine converts a topic into a full debate and final result.

## Engine modules

## `state.py`
Defines core domain objects:
- `Side`: `pro` or `con`
- `ReasoningType`: `causal`, `tradeoff`, `ethical`, `risk`
- `Argument`: claim, premises, inference, optional attack target, strength
- `RoundRecord`: one move with resulting belief
- `DebateState`: full debate state + serialization helpers

## `reasoning.py`
`ArgumentGenerator` creates argument candidates by side, topic, claims, and history.

Characteristics:
- deterministic when seed is provided,
- round-aware variation,
- rebuttal behavior against opponent's latest move,
- structured argument output suitable for UI display.

## `belief.py`
`BeliefModel` manages audience stance in `[0, 1]`.

- Start prior defaults to `0.5`.
- Each move updates belief based on argument strengths.
- Values are clamped so output stays bounded.

## `minimax.py`
`MinimaxAgent` evaluates candidate moves with alpha-beta pruning.

- Pro acts as maximizer.
- Con acts as minimizer.
- Recursive search alternates sides.
- Pruning events are captured in `pruning_log`.

Terminal condition:
- Search stops when configured full rounds are exhausted:
  - `state.round_number >= state.max_rounds * 2`

## `debate.py`
`DebateRunner` orchestrates full simulation:
1. initialize claims (API facts or template facts),
2. initialize state,
3. iterate moves (Pro then Con),
4. update belief and history each move,
5. derive winner and turning point.

---

## Execution flow

```text
Topic -> initial claims -> DebateState
      -> Pro selects best argument via minimax
      -> belief update
      -> Con selects best argument via minimax
      -> belief update
      -> repeat until max rounds complete
      -> compute winner + turning point + summary
```

---

## Winner and turning point

- **Winner**
  - belief `> 0.5` => Pro
  - belief `< 0.5` => Con
  - otherwise tie (`None` in state, `tie` in summary)

- **Turning point round**
  - computed as the round with largest absolute belief swing between consecutive history points.

---

## Performance characteristics

- Candidate generation drives branching factor.
- Search depth defaults to `3`.
- Alpha-beta pruning significantly reduces explored branches.
- Current implementation is intentionally single-threaded and in-memory for clarity.

Potential optimizations:
- transposition table / memoization for repeated state evaluations,
- move ordering heuristics to improve pruning quality,
- optional depth tuning based on candidate count,
- batched scoring for candidate pre-filtering.

---

## Design constraints

- No database persistence (single active debate in process memory).
- No user/session isolation for concurrent debates.
- Fallback content generation must always work without external APIs.

