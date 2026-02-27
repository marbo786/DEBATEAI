# DebateAI Engine compatibility exports
from backend.domain.state import DebateState, Argument, Side
from backend.domain.reasoning import ArgumentGenerator
from backend.domain.belief import BeliefModel
from backend.domain.minimax import MinimaxAgent
from backend.engine.debate import DebateRunner

__all__ = [
    "DebateState",
    "Argument",
    "Side",
    "ArgumentGenerator",
    "BeliefModel",
    "MinimaxAgent",
    "DebateRunner",
    "DebateStrategy",
    "MinimaxStrategy",
    "MonteCarloRolloutStrategy",
    "BeamSearchStrategy",
]
