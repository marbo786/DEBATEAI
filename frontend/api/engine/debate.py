"""
Debate orchestrator: run 4-6 rounds, minimax selects moves, belief updates.
Computes winner and turning point.
"""
from .state import DebateState, Side, RoundRecord
from .reasoning import ArgumentGenerator
from .belief import BeliefModel
from .minimax import MinimaxAgent


class DebateRunner:
    """
    Runs a full debate: init claims, then each round Pro and Con each
    choose an argument via minimax; belief updates after each move.
    """

    def __init__(
        self,
        max_rounds: int = 6,
        seed: int | None = None,
    ):
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

    def run(
        self,
        topic: str,
        initial_pro: list[str] | None = None,
        initial_con: list[str] | None = None,
    ) -> tuple[DebateState, list[dict]]:
        """
        Run full debate. Returns (final DebateState, list of pruning_log dicts per move).
        If initial_pro and initial_con are provided, use them; else generate via ArgumentGenerator.
        """
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
        pruning_logs = []

        for r in range(self.max_rounds):
            # Pro move
            best_pro, _ = self.minimax_pro.get_best_argument(state, Side.PRO)
            if best_pro:
                state = self._apply(state, Side.PRO, best_pro)
                pruning_logs.append({
                    "side": "pro",
                    "round": r + 1,
                    "pruning_log": self.minimax_pro.get_pruning_log_dict(),
                })

            # One round = Pro move + Con move; stop after max_rounds full rounds
            if (state.round_number // 2) >= state.max_rounds:
                break

            # Con move
            best_con, _ = self.minimax_con.get_best_argument(state, Side.CON)
            if best_con:
                state = self._apply(state, Side.CON, best_con)
                pruning_logs.append({
                    "side": "con",
                    "round": r + 1,
                    "pruning_log": self.minimax_con.get_pruning_log_dict(),
                })

            if (state.round_number // 2) >= state.max_rounds:
                break

        state.winner = self._winner(state)
        state.turning_point_round = self._turning_point(state)
        return state, pruning_logs

    def _apply(self, state: DebateState, side: Side, argument) -> DebateState:
        pro_arg = argument if side == Side.PRO else None
        con_arg = argument if side == Side.CON else None
        new_belief = self.belief_model.update_from_arguments(
            state.belief, pro_arg, con_arg
        )
        state.history.append(
            RoundRecord(side=side, argument=argument, belief_after=new_belief)
        )
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
        """Round (1-based) with largest belief swing from previous."""
        if len(state.belief_history) < 2:
            return None
        max_swing = 0.0
        turn_round = None
        for i in range(1, len(state.belief_history)):
            swing = abs(state.belief_history[i] - state.belief_history[i - 1])
            if swing > max_swing:
                max_swing = swing
                # Map history index to round: 2 moves per round
                turn_round = (i // 2) + 1
        return turn_round or 1
