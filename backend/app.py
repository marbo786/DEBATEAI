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
        self.facts_from_api: bool = False


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


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.route("/api/start", methods=["POST"])
    def start() -> tuple[Any, int] | Any:
        """Start and run a full debate."""
        data = request.get_json(silent=True) or {}
        topic = (data.get("topic") or "").strip()
        if not topic:
            return jsonify({"error": "topic is required"}), 400

        try:
            requested_rounds = parse_int(data.get("max_rounds"), 6, "max_rounds")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        max_rounds = min(6, max(4, requested_rounds))
        api_facts = get_facts_from_groq(topic)
        store.facts_from_api = bool(api_facts)
        initial_pro, initial_con = api_facts if api_facts else (None, None)

        runner = DebateRunner(max_rounds=max_rounds)
        store.state, store.pruning_logs = runner.run(
            topic,
            initial_pro=initial_pro,
            initial_con=initial_con,
        )

        return jsonify(
            {
                "state": store.state.to_dict(),
                "summary": _summary(store.state),
                "pruning_logs": store.pruning_logs,
                "facts_from_api": store.facts_from_api,
            }
        )

    @app.route("/api/state", methods=["GET"])
    def state() -> Any:
        """Return current in-memory state and summary."""
        if store.state is None:
            return jsonify({"state": None, "summary": None})

        return jsonify(
            {
                "state": store.state.to_dict(),
                "summary": _summary(store.state),
            }
        )

    @app.route("/api/summary", methods=["GET", "POST"])
    def summary() -> tuple[Any, int] | Any:
        """Return summary, optionally with override audience belief."""
        if store.state is None:
            return jsonify({"error": "no debate run yet"}), 404

        override: float | None = None
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            raw_override = data.get("override_audience")
            if raw_override is not None:
                try:
                    override = clamp(
                        parse_float(raw_override, "override_audience"),
                        0.0,
                        1.0,
                    )
                except ValueError as exc:
                    return jsonify({"error": str(exc)}), 400

        return jsonify(_summary(store.state, override_belief=override))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
