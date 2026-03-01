"""
Knowledge representation for DebateAI.
Structured debate state, arguments, and argument history.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Side(str, Enum):
    PRO = "pro"
    CON = "con"


class ReasoningType(str, Enum):
    CAUSAL = "causal"
    TRADEOFF = "tradeoff"
    ETHICAL = "ethical"
    RISK = "risk"


@dataclass
class Argument:
    """Structured argument: claim, premises, optional attack, strength."""

    claim: str
    premises: list[str]
    inference: str
    attack_target: Optional[int] = None  # index in opponent's history, or None
    strength: float = 0.0  # 0..1
    reasoning_type: str = "causal"

    def to_dict(self) -> dict:
        return {
            "claim": self.claim,
            "premises": self.premises,
            "inference": self.inference,
            "attack_target": self.attack_target,
            "strength": self.strength,
            "reasoning_type": self.reasoning_type,
        }


@dataclass
class RoundRecord:
    """Single round: who spoke, which argument, belief after."""

    side: Side
    argument: Argument
    belief_after: float

    def to_dict(self) -> dict:
        return {
            "side": self.side.value,
            "argument": self.argument.to_dict(),
            "belief_after": self.belief_after,
        }


@dataclass
class DebateState:
    """
    Full debate state: topic, claims per side, argument history, audience belief.
    """

    topic: str
    pro_claims: list[str] = field(default_factory=list)
    con_claims: list[str] = field(default_factory=list)
    history: list[RoundRecord] = field(default_factory=list)
    belief: float = 0.5
    belief_history: list[float] = field(default_factory=lambda: [0.5])
    round_number: int = 0
    max_rounds: int = 6
    winner: Optional[Side] = None
    turning_point_round: Optional[int] = None

    def to_dict(self) -> dict:
        # "round" = current debate round (1-based), not move count
        display_round = min(self.max_rounds, (self.round_number + 1) // 2)
        return {
            "topic": self.topic,
            "round": display_round,
            "belief": self.belief,
            "pro_claims": self.pro_claims.copy(),
            "con_claims": self.con_claims.copy(),
            "history": [r.to_dict() for r in self.history],
            "winner": self.winner.value if self.winner else None,
            "turning_point_round": self.turning_point_round,
            "max_rounds": self.max_rounds,
        }

    def copy(self) -> "DebateState":
        return DebateState(
            topic=self.topic,
            pro_claims=self.pro_claims.copy(),
            con_claims=self.con_claims.copy(),
            history=[r for r in self.history],
            belief=self.belief,
            belief_history=self.belief_history.copy(),
            round_number=self.round_number,
            max_rounds=self.max_rounds,
            winner=self.winner,
            turning_point_round=self.turning_point_round,
        )
