# DebateAI Engine compatibility exports
try:
    from backend.domain.state import DebateState, Argument, Side
    from backend.domain.reasoning import ArgumentGenerator
    from backend.domain.belief import BeliefModel
    from backend.domain.minimax import MinimaxAgent
    from backend.engine.debate import DebateRunner
except ModuleNotFoundError:  # Vercel backend project rooted at /backend
    from domain.state import DebateState, Argument, Side
    from domain.reasoning import ArgumentGenerator
    from domain.belief import BeliefModel
    from domain.minimax import MinimaxAgent
    from engine.debate import DebateRunner

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
