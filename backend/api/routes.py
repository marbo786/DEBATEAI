"""Flask routes/controllers for DebateAI API."""
from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request

from backend.services.debate_service import DebateService
from backend.domain.state import DebateState

api_bp = Blueprint("api", __name__, url_prefix="/api")


class DebateStore:
    """In-memory state for one active debate."""

    def __init__(self) -> None:
        self.state: DebateState | None = None
        self.pruning_logs: list[dict] | None = None
        self.facts_from_api: bool = False


def _service() -> DebateService:
    return current_app.config["debate_service"]


def _store() -> DebateStore:
    return current_app.config["debate_store"]


def _facts_provider():
    return current_app.config["facts_provider"]


def _parse_int(value: Any, default: int, field_name: str) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


@api_bp.route("/start", methods=["POST"])
def start() -> tuple[Any, int] | Any:
    data = request.get_json() or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic is required"}), 400

    try:
        requested_rounds = _parse_int(data.get("max_rounds"), 6, "max_rounds")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    result = _service().run_debate(topic, requested_rounds, _facts_provider())

    store = _store()
    store.state = result.state
    store.pruning_logs = result.pruning_logs
    store.facts_from_api = result.facts_from_api

    return jsonify(
        {
            "state": result.state.to_dict(),
            "summary": _service().summarize(result.state),
            "pruning_logs": result.pruning_logs,
            "facts_from_api": result.facts_from_api,
        }
    )


@api_bp.route("/state", methods=["GET"])
def state() -> Any:
    current_state = _store().state
    if current_state is None:
        return jsonify({"state": None, "summary": None})

    return jsonify(
        {
            "state": current_state.to_dict(),
            "summary": _service().summarize(current_state),
        }
    )


@api_bp.route("/summary", methods=["GET", "POST"])
def summary() -> tuple[Any, int] | Any:
    current_state = _store().state
    if current_state is None:
        return jsonify({"error": "no debate run yet"}), 404

    if request.method == "POST":
        data = request.get_json() or {}
        value = data.get("override_audience")
        if value is not None:
            try:
                override = max(0.0, min(1.0, float(value)))
            except (TypeError, ValueError):
                return jsonify({"error": "override_audience must be a number between 0 and 1"}), 400
            return jsonify(_service().summarize(current_state, override_belief=override))

    return jsonify(_service().summarize(current_state))
