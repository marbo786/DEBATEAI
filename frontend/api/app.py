"""
Flask API for DebateAI. Endpoints: start debate, state, summary.
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from engine.debate import DebateRunner
from engine.facts_api import get_facts_from_groq
from engine.state import DebateState

app = Flask(__name__)
CORS(app)

# In-memory state for one active debate
_current_state: DebateState | None = None
_current_pruning_logs: list | None = None


def _summary(state: DebateState, override_belief: float | None = None) -> dict:
    belief = override_belief if override_belief is not None else state.belief
    if override_belief is not None:
        winner = "pro" if belief > 0.5 else "con" if belief < 0.5 else "tie"
    else:
        winner = state.winner.value if state.winner else "tie"
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

    max_rounds = min(6, max(4, int(data.get("max_rounds", 6))))
    api_facts = get_facts_from_groq(topic)
    facts_from_api = bool(api_facts)
    initial_pro, initial_con = api_facts if api_facts else (None, None)
    runner = DebateRunner(max_rounds=max_rounds)
    _current_state, _current_pruning_logs = runner.run(
        topic, initial_pro=initial_pro, initial_con=initial_con
    )

    return jsonify({
        "state": _current_state.to_dict(),
        "summary": _summary(_current_state),
        "pruning_logs": _current_pruning_logs,
        "facts_from_api": facts_from_api,
    })


@app.route("/api/state", methods=["GET"])
def state():
    """Return current debate state if any."""
    if _current_state is None:
        return jsonify({"state": None, "summary": None})
    return jsonify({
        "state": _current_state.to_dict(),
        "summary": _summary(_current_state),
    })


@app.route("/api/summary", methods=["GET", "POST"])
def summary():
    """Return summary; POST body may include override_audience (0-1) to recalc percentages."""
    if _current_state is None:
        return jsonify({"error": "no debate run yet"}), 404
    override = None
    if request.method == "POST":
        data = request.get_json() or {}
        v = data.get("override_audience")
        if v is not None:
            override = max(0.0, min(1.0, float(v)))
    return jsonify(_summary(_current_state, override_belief=override))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
