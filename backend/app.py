"""Flask app factory for DebateAI."""
from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from backend.api.routes import DebateStore, api_bp
from backend.infra.groq_client import get_facts_from_groq
from backend.services.debate_service import DebateService


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    app.config["debate_service"] = DebateService()
    app.config["debate_store"] = DebateStore()
    app.config["facts_provider"] = get_facts_from_groq

    app.register_blueprint(api_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
