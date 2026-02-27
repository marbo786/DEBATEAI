"""Debate orchestration use-cases independent of delivery framework."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

try:
    from backend.domain.belief import BeliefModel
    from backend.domain.minimax import MinimaxAgent
    from backend.domain.reasoning import ArgumentGenerator
    from backend.domain.state import DebateState, RoundRecord, Side
except ModuleNotFoundError:  # Vercel backend project rooted at /backend
    from domain.belief import BeliefModel
    from domain.minimax import MinimaxAgent
    from domain.reasoning import ArgumentGenerator
    from domain.state import DebateState, RoundRecord, Side

FactsProvider = Callable[[str], tuple[list[str], list[str]] | None]


@dataclass
class DebateResult:
    state: DebateState
    pruning_logs: list[dict]
    facts_from_api: bool


class DebateService:
    """Runs complete debates and computes summaries."""

    def __init__(self, max_rounds: int = 6, seed: int | None = None) -> None:
        self.max_rounds = max_rounds
        self.arg_gen = ArgumentGenerator(seed=seed)
        self.belief_model = BeliefModel(sensitivity=0.12, prior=0.5)
        self.minimax_pro = MinimaxAgent(
            argument_generator=self.arg_gen,
            belief_model=self.belief_model,
            depth=3,
        )
        self.minimax_con = MinimaxAgent(
            argument_generator=self.arg_gen,
            belief_model=self.belief_model,
            depth=3,
        )

    def run_debate(
        self,
        topic: str,
        rounds: int,
        facts_provider: FactsProvider | None = None,
    ) -> DebateResult:
        max_rounds = min(6, max(4, rounds))
        api_facts = facts_provider(topic) if facts_provider else None
        facts_from_api = bool(api_facts)

        if api_facts is not None:
            pro_claims, con_claims = api_facts
        else:
            pro_claims, con_claims = self.arg_gen.generate_initial_claims(topic)

        state = DebateState(
            topic=topic,
            pro_claims=pro_claims,
            con_claims=con_claims,
            history=[],
            belief=self.belief_model.prior,
            belief_history=[self.belief_model.prior],
            round_number=0,
            max_rounds=max_rounds,
        )

        pruning_logs: list[dict] = []
        for debate_round in range(max_rounds):
            best_pro, _ = self.minimax_pro.get_best_argument(state, Side.PRO)
            if best_pro:
                state = self._apply(state, Side.PRO, best_pro)
                pruning_logs.append(
                    {
                        "side": "pro",
                        "round": debate_round + 1,
                        "pruning_log": self.minimax_pro.get_pruning_log_dict(),
                    }
                )

            if (state.round_number // 2) >= state.max_rounds:
                break

            best_con, _ = self.minimax_con.get_best_argument(state, Side.CON)
            if best_con:
                state = self._apply(state, Side.CON, best_con)
                pruning_logs.append(
                    {
                        "side": "con",
                        "round": debate_round + 1,
                        "pruning_log": self.minimax_con.get_pruning_log_dict(),
                    }
                )

            if (state.round_number // 2) >= state.max_rounds:
                break

        state.winner = self._winner(state)
        state.turning_point_round = self._turning_point(state)
        return DebateResult(
            state=state,
            pruning_logs=pruning_logs,
            facts_from_api=facts_from_api,
        )

    def summarize(self, state: DebateState, override_belief: float | None = None) -> dict:
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

    def _apply(self, state: DebateState, side: Side, argument) -> DebateState:
        pro_arg = argument if side == Side.PRO else None
        con_arg = argument if side == Side.CON else None
        new_belief = self.belief_model.update_from_arguments(state.belief, pro_arg, con_arg)
        state.history.append(RoundRecord(side=side, argument=argument, belief_after=new_belief))
        state.belief = new_belief
        state.belief_history.append(new_belief)
        state.round_number += 1
        return state

    @staticmethod
    def _winner(state: DebateState) -> Side | None:
        if state.belief > 0.5:
            return Side.PRO
        if state.belief < 0.5:
            return Side.CON
        return None

    @staticmethod
    def _turning_point(state: DebateState) -> int | None:
        if len(state.belief_history) < 2:
            return None
        max_swing = 0.0
        turn_round = None
        for i in range(1, len(state.belief_history)):
            swing = abs(state.belief_history[i] - state.belief_history[i - 1])
            if swing > max_swing:
                max_swing = swing
                turn_round = (i // 2) + 1
        return turn_round or 1
