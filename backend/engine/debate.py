"""Debate orchestrator with pluggable solver strategies."""
from __future__ import annotations

from .belief import BeliefModel
from .reasoning import ArgumentGenerator
from .state import DebateState, RoundRecord, Side
from .strategies import DebateStrategy, build_strategy


class DebateRunner:
    """Run a full debate by delegating move selection to a strategy."""

    def __init__(
        self,
        max_rounds: int = 6,
        seed: int | None = None,
        strategy: str | DebateStrategy | None = "minimax",
    ):
        self.max_rounds = max_rounds
        self.arg_gen = ArgumentGenerator(seed=seed)
        self.belief_model = BeliefModel(sensitivity=0.12, prior=0.5)
        self.strategy = build_strategy(strategy, self.arg_gen, self.belief_model, seed=seed)

    def run(
        self,
        topic: str,
        initial_pro: list[str] | None = None,
        initial_con: list[str] | None = None,
    ) -> tuple[DebateState, list[dict]]:
        if initial_pro is not None and initial_con is not None:
            pro_claims, con_claims = initial_pro, initial_con
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
            max_rounds=self.max_rounds,
        )
        decision_logs: list[dict] = []

        for r in range(self.max_rounds):
            best_pro, score_pro = self.strategy.propose_move(state, Side.PRO)
            if best_pro:
                state = self._apply(state, Side.PRO, best_pro)
                decision_logs.append(
                    {
                        "side": "pro",
                        "round": r + 1,
                        "score": score_pro,
                        "details": self.strategy.explain_decision(),
                    }
                )

            if (state.round_number // 2) >= state.max_rounds:
                break

            best_con, score_con = self.strategy.propose_move(state, Side.CON)
            if best_con:
                state = self._apply(state, Side.CON, best_con)
                decision_logs.append(
                    {
                        "side": "con",
                        "round": r + 1,
                        "score": score_con,
                        "details": self.strategy.explain_decision(),
                    }
                )

            if (state.round_number // 2) >= state.max_rounds:
                break

        state.winner = self._winner(state)
        state.turning_point_round = self._turning_point(state)
        return state, decision_logs

    def strategy_metadata(self) -> dict:
        return {
            "id": self.strategy.strategy_id,
            "name": self.strategy.display_name,
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

    def _winner(self, state: DebateState) -> Side | None:
        if state.belief > 0.5:
            return Side.PRO
        if state.belief < 0.5:
            return Side.CON
        return None

    def _turning_point(self, state: DebateState) -> int | None:
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
