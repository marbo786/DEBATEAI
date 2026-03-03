"""FastAPI routes/controllers for DebateAI API."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.services.debate_service import DebateService
    from backend.domain.state import DebateState, Persona, Side
    from backend.domain.reasoning import parse_user_argument
    from backend.infra.database import get_db
    from backend.infra.models import DebateRecord
    from backend.infra.groq_client import generate_completion
except ModuleNotFoundError:  # Vercel backend project rooted at /backend
    from services.debate_service import DebateService
    from domain.state import DebateState, Persona, Side
    from domain.reasoning import parse_user_argument
    from infra.database import get_db
    from infra.models import DebateRecord
    from infra.groq_client import generate_completion

router = APIRouter(prefix="/api")


class StartRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500, strip_whitespace=True)
    max_rounds: Optional[int] = Field(default=6, ge=2, le=10)
    persona: Optional[str] = Field(default="default", max_length=50)
    user_side: Optional[str] = Field(default="auto", max_length=10)


class SummaryOverrideRequest(BaseModel):
    override_audience: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class UserMoveRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, strip_whitespace=True)


@router.post("/start")
async def start(req: Request, data: StartRequest, db: AsyncSession = Depends(get_db)) -> Any:
    debate_service: DebateService = req.app.state.debate_service
    facts_provider = req.app.state.facts_provider

    result = await debate_service.initialize_debate(
        data.topic, data.max_rounds, facts_provider, data.persona, data.user_side, db
    )
    return {
        "debate_id": str(result.state.id) if result.state.id else None,
        "state": result.state.to_dict(),
        "summary": debate_service.summarize(result.state),
        "pruning_logs": result.pruning_logs,
        "facts_from_api": result.facts_from_api,
    }

@router.get("/debate/{debate_id}/stream_turn")
async def stream_turn(req: Request, debate_id: str, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    debate_service: DebateService = req.app.state.debate_service

    current_state = await debate_service.get_debate_state(debate_id, db)
    if current_state is None:
        raise HTTPException(status_code=404, detail="debate not found")

    async def event_generator():
        async for chunk in debate_service.run_turn_stream(debate_id, db):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/state/{debate_id}")
async def state(req: Request, debate_id: str, db: AsyncSession = Depends(get_db)) -> Any:
    debate_service: DebateService = req.app.state.debate_service
    current_state = await debate_service.get_debate_state(debate_id, db)
    if current_state is None:
        raise HTTPException(status_code=404, detail="debate not found")

    return {
        "state": current_state.to_dict(),
        "summary": debate_service.summarize(current_state),
    }


@router.api_route("/summary/{debate_id}", methods=["GET", "POST"])
async def summary(
    req: Request,
    debate_id: str,
    data: SummaryOverrideRequest = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    debate_service: DebateService = req.app.state.debate_service
    current_state = await debate_service.get_debate_state(debate_id, db)
    if current_state is None:
        raise HTTPException(status_code=404, detail="debate not found")

    if req.method == "POST" and data and data.override_audience is not None:
        override = max(0.0, min(1.0, data.override_audience))
        return debate_service.summarize(current_state, override_belief=override)

    return debate_service.summarize(current_state)


@router.post("/debate/{debate_id}/move")
async def user_move(
    req: Request,
    debate_id: str,
    data: UserMoveRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    debate_service: DebateService = req.app.state.debate_service
    current_state = await debate_service.get_debate_state(debate_id, db)

    if current_state is None:
        raise HTTPException(status_code=404, detail="debate not found")
    if current_state.round_number // 2 >= current_state.max_rounds:
        raise HTTPException(status_code=400, detail="debate is already finished")

    # Determine side based on move count (even = PRO's turn, odd = CON's turn)
    side = Side.PRO if current_state.round_number % 2 == 0 else Side.CON

    # Semantically analyze user text via Groq (falls back to heuristics if unavailable)
    argument = await parse_user_argument(data.text, groq_completion=generate_completion)

    result = await db.execute(sa_select(DebateRecord).where(DebateRecord.id == debate_id))
    db_debate = result.scalar_one()

    new_state = await debate_service._apply(current_state, side, argument, db, db_debate)
    return {
        "state": new_state.to_dict(),
        "summary": debate_service.summarize(new_state),
    }
