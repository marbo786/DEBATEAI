"""FastAPI routes/controllers for DebateAI API."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.services.debate_service import DebateService
    from backend.domain.state import DebateState, Persona
    from backend.infra.database import get_db
    from backend.infra.models import DebateRecord
except ModuleNotFoundError:  # Vercel backend project rooted at /backend
    from services.debate_service import DebateService
    from domain.state import DebateState, Persona
    from infra.database import get_db
    from infra.models import DebateRecord

router = APIRouter(prefix="/api")

class StartRequest(BaseModel):
    topic: str
    max_rounds: Optional[int] = 6
    persona: Optional[str] = "default"
    user_side: Optional[str] = "auto"

class SummaryOverrideRequest(BaseModel):
    override_audience: Optional[float] = None

class UserMoveRequest(BaseModel):
    text: str

@router.post("/start")
async def start(req: Request, data: StartRequest, db: AsyncSession = Depends(get_db)) -> Any:
    topic = data.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")
    
    debate_service: DebateService = req.app.state.debate_service
    facts_provider = req.app.state.facts_provider

    # Only initialize DB record + generate claims - do NOT run the full simulation.
    # The frontend drives each turn individually via GET /debate/{id}/stream_turn.
    result = await debate_service.initialize_debate(topic, data.max_rounds, facts_provider, data.persona, data.user_side, db)

    return {
        "debate_id": str(result.state.id) if hasattr(result.state, 'id') else None,
        "state": result.state.to_dict(),
        "summary": debate_service.summarize(result.state),
        "pruning_logs": result.pruning_logs,
        "facts_from_api": result.facts_from_api,
    }

@router.get("/stream")
async def stream(req: Request, topic: str, max_rounds: Optional[int] = 6, persona: Optional[str] = "default", user_side: Optional[str] = "auto", db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    topic = topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")
        
    debate_service: DebateService = req.app.state.debate_service
    facts_provider = req.app.state.facts_provider

    async def event_generator():
        async for chunk in debate_service.run_debate_stream(topic, max_rounds, facts_provider, persona, user_side, db):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")

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
async def summary(req: Request, debate_id: str, data: SummaryOverrideRequest = None, db: AsyncSession = Depends(get_db)) -> Any:
    debate_service: DebateService = req.app.state.debate_service
    current_state = await debate_service.get_debate_state(debate_id, db)
    if current_state is None:
        raise HTTPException(status_code=404, detail="debate not found")
    
    if req.method == "POST" and data and data.override_audience is not None:
        override = max(0.0, min(1.0, data.override_audience))
        return debate_service.summarize(current_state, override_belief=override)

    return debate_service.summarize(current_state)

@router.post("/debate/{debate_id}/move")
async def user_move(req: Request, debate_id: str, data: UserMoveRequest, db: AsyncSession = Depends(get_db)) -> Any:
    text = data.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
        
    debate_service: DebateService = req.app.state.debate_service
    current_state = await debate_service.get_debate_state(debate_id, db)
    
    if current_state is None:
        raise HTTPException(status_code=404, detail="debate not found")
        
    if current_state.round_number // 2 >= current_state.max_rounds:
        raise HTTPException(status_code=400, detail="debate is already finished")
        
    # Determine side based on round_number (even=PRO, odd=CON)
    side = Side.PRO if current_state.round_number % 2 == 0 else Side.CON
    
    # Process user argument
    argument = await debate_service.arg_gen.parse_user_argument(text)
    
    try:
        from backend.infra.models import DebateRecord
    except ModuleNotFoundError:
        from infra.models import DebateRecord

    from sqlalchemy import select
    result = await db.execute(select(DebateRecord).where(DebateRecord.id == debate_id))
    db_debate = result.scalar_one()
    
    new_state = await debate_service._apply(current_state, side, argument, db, db_debate)
    
    return {
        "state": new_state.to_dict(),
        "summary": debate_service.summarize(new_state)
    }
