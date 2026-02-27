"""Flask API for DebateAI."""
from __future__ import annotations

from flask import Flask, jsonify, request
from flask_cors import CORS

from engine.debate import DebateRunner
from engine.facts_api import get_facts_from_groq
from engine.state import DebateState

app = Flask(__name__)
CORS(app)


class DebateStore:
    """In-memory state for one active debate."""

    def __init__(self) -> None:
        self.state: DebateState | None = None
        self.decision_logs: list[dict] | None = None
        self.strategy: dict | None = None


store = DebateStore()


def _summary(state: DebateState, override_belief: float | None = None) -> dict:
    belief = override_belief if override_belief is not None else state.belief
    winner = (
        ("pro" if belief > 0.5 else "con" if belief < 0.5 else "tie")
        if override_belief is not None
        else (state.winner.value if state.winner else "tie")
    )
    return {
        "topic": state.topic,
        "winner": winner,
        "final_belief": belief,
        "final_pro_pct": round(belief * 100, 1),
        "final_con_pct": round((1 - belief) * 100, 1),
        "turning_point_round": state.turning_point_round,
        "total_rounds": state.round_number,
    }


@app.route("/api/start", methods=["POST"])
def start() -> tuple:
    """Start a new debate.

    Body example:
    {
      "topic": "...",
      "max_rounds": 6,
      "strategy": "minimax|mcts|beam",
      "override_audience": 0.6
    }
    """
    data = request.get_json() or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic is required"}), 400

    try:
        requested_rounds = int(data.get("max_rounds", 6))
    except (TypeError, ValueError):
        return jsonify({"error": "max_rounds must be an integer"}), 400

    strategy_id = str(data.get("strategy", "minimax")).lower()
    if strategy_id not in {"minimax", "mcts", "beam"}:
        return jsonify({"error": "strategy must be one of minimax, mcts, beam"}), 400

    override = data.get("override_audience")
    if override is not None:
        try:
            override = max(0.0, min(1.0, float(override)))
        except (TypeError, ValueError):
            return jsonify({"error": "override_audience must be a number between 0 and 1"}), 400

    max_rounds = min(6, max(4, requested_rounds))
    api_facts = get_facts_from_groq(topic)
    facts_from_api = bool(api_facts)
    initial_pro, initial_con = api_facts if api_facts else (None, None)

    try:
        runner = DebateRunner(max_rounds=max_rounds, strategy=strategy_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    state, decision_logs = runner.run(topic, initial_pro=initial_pro, initial_con=initial_con)
    store.state = state
    store.decision_logs = decision_logs
    store.strategy = runner.strategy_metadata()

    return (
        jsonify(
            {
                "state": state.to_dict(),
                "summary": _summary(state, override_belief=override),
                "decision_logs": decision_logs,
                "strategy": store.strategy,
                "facts_from_api": facts_from_api,
            }
        ),
        200,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
