"""Flask API for DebateAI."""
from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS

from engine.debate import DebateRunner
from engine.facts_api import get_facts_from_groq
from engine.state import DebateState


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def parse_int(value: Any, default: int, field_name: str) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def parse_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number between 0 and 1") from exc


class DebateStore:
    """In-memory state for one active debate."""

    def __init__(self) -> None:
        self.state: DebateState | None = None
        self.pruning_logs: list[dict] | None = None


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
def start():
    """Start a new debate. Body: { "topic": "string" }. Runs full debate, returns state + summary."""
    global _current_state, _current_pruning_logs
    data = request.get_json() or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic is required"}), 400

    try:
        requested_rounds = int(data.get("max_rounds", 6))
    except (TypeError, ValueError):
        return jsonify({"error": "max_rounds must be an integer"}), 400

    max_rounds = min(6, max(4, requested_rounds))
    api_facts = get_facts_from_groq(topic)
    facts_from_api = bool(api_facts)
    initial_pro, initial_con = api_facts if api_facts else (None, None)
    runner = DebateRunner(max_rounds=max_rounds)
    _current_state, _current_pruning_logs = runner.run(
        topic, initial_pro=initial_pro, initial_con=initial_con
    )

    @app.route("/api/start", methods=["POST"])
    def start():
        data = request.get_json() or {}
        v = data.get("override_audience")
        if v is not None:
            try:
                override = max(0.0, min(1.0, float(v)))
            except (TypeError, ValueError):
                return jsonify({"error": "override_audience must be a number between 0 and 1"}), 400
    return jsonify(_summary(_current_state, override_belief=override))

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
