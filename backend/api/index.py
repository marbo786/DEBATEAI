"""FastAPI app factory for DebateAI."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from api.routes import router
    from infra.groq_client import get_facts_from_groq
    from services.debate_service import DebateService
except ModuleNotFoundError:
    from backend.api.routes import router
    from backend.infra.groq_client import get_facts_from_groq
    from backend.services.debate_service import DebateService


def create_app() -> FastAPI:
    """Create and configure the FastAPI app instance."""
    app = FastAPI(title="DebateAI API")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from fastapi.responses import JSONResponse
    from starlette.requests import Request
    import traceback

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import logging
        logging.error(f"Global Error: {exc}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "trace": traceback.format_exc()},
            headers={"Access-Control-Allow-Origin": "*"}
        )

    @app.get("/")
    def read_root():
        return {"status": "ok", "message": "DebateAI Backend is running!"}

    app.state.debate_service = DebateService()
    app.state.facts_provider = get_facts_from_groq

    app.include_router(router)
    return app

app = create_app()
