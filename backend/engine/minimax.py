"""
Adversarial search: Minimax with Alpha-Beta pruning.
Pro maximizes belief impact, Con minimizes. Depth 2-3, pruning logged.
"""
from dataclasses import dataclass, field
from .state import DebateState, Argument, Side, RoundRecord
from .reasoning import ArgumentGenerator
from .belief import BeliefModel


@dataclass
class PruningLogEntry:
    """One pruned branch for demonstration."""
    depth: int
    side: str
    action_description: str
    cut_type: str  # "alpha" or "beta"
    value: float
    alpha: float
    beta: float


def eval_state(state: DebateState, belief_model: BeliefModel, side: Side) -> float:
    """
    Evaluation for minimax: from Pro's perspective (higher = better for Pro).
    Combines: current belief (Pro wants high), last argument strengths, consistency.
    """
    score = state.belief  # 0..1, Pro wants to maximize
    # Small bonus/penalty from last round if any
    if state.history:
        last = state.history[-1]
        if last.side == Side.PRO:
            score += 0.1 * last.argument.strength
        else:
            score -= 0.1 * last.argument.strength
    return max(0.0, min(1.0, score))


def apply_move(
    state: DebateState,
    side: Side,
    argument: Argument,
    belief_model: BeliefModel,
) -> DebateState:
    """Apply one move: append to history and update belief."""
    pro_arg = argument if side == Side.PRO else None
    con_arg = argument if side == Side.CON else None
    new_belief = belief_model.update_from_arguments(
        state.belief, pro_arg, con_arg
    )
    new_history = state.history + [
        RoundRecord(side=side, argument=argument, belief_after=new_belief)
    ]
    new_state = state.copy()
    new_state.history = new_history
    new_state.belief = new_belief
    new_state.belief_history = state.belief_history + [new_belief]
    new_state.round_number = state.round_number + 1
    return new_state


class MinimaxAgent:
    """
    Minimax with Alpha-Beta pruning. Pro = maximizer, Con = minimizer.
    Depth 2-3; logs pruned branches.
    """

    def __init__(
        self,
        argument_generator: ArgumentGenerator,
        belief_model: BeliefModel,
        depth: int = 3,
    ):
        self.arg_gen = argument_generator
        self.belief_model = belief_model
        self.depth = depth
        self.pruning_log: list[PruningLogEntry] = []

    def get_best_argument(
        self,
        state: DebateState,
        side: Side,
    ) -> tuple[Argument | None, float]:
        """
        Returns (best argument, value). Uses alpha-beta; fills pruning_log.
        """
        self.pruning_log.clear()
        candidates = self.arg_gen.generate_arguments(
            side=side,
            topic=state.topic,
            pro_claims=state.pro_claims,
            con_claims=state.con_claims,
            history=state.history,
            count=6,
        )
        if not candidates:
            return None, eval_state(state, self.belief_model, side)

        alpha, beta = -float("inf"), float("inf")
        best_arg = candidates[0]
        best_val = -float("inf") if side == Side.PRO else float("inf")

        for arg in candidates:
            child = apply_move(state, side, arg, self.belief_model)
            if side == Side.PRO:
                val = self._minimax_min(child, self.depth - 1, alpha, beta)
                if val > best_val:
                    best_val = val
                    best_arg = arg
                alpha = max(alpha, best_val)
            else:
                val = self._minimax_max(child, self.depth - 1, alpha, beta)
                if val < best_val:
                    best_val = val
                    best_arg = arg
                beta = min(beta, best_val)
            if beta <= alpha:
                self.pruning_log.append(
                    PruningLogEntry(
                        depth=self.depth,
                        side=side.value,
                        action_description=arg.claim[:50] + "...",
                        cut_type="beta" if side == Side.PRO else "alpha",
                        value=val,
                        alpha=alpha,
                        beta=beta,
                    )
                )
                break

        return best_arg, best_val

    def _minimax_max(
        self, state: DebateState, depth: int, alpha: float, beta: float
    ) -> float:
        if depth <= 0 or state.round_number >= state.max_rounds:
            return eval_state(state, self.belief_model, Side.PRO)
        candidates = self.arg_gen.generate_arguments(
            Side.PRO,
            state.topic,
            state.pro_claims,
            state.con_claims,
            state.history,
            count=4,
        )
        if not candidates:
            return eval_state(state, self.belief_model, Side.PRO)
        v = -float("inf")
        for arg in candidates:
            child = apply_move(state, Side.PRO, arg, self.belief_model)
            v = max(v, self._minimax_min(child, depth - 1, alpha, beta))
            alpha = max(alpha, v)
            if beta <= alpha:
                self.pruning_log.append(
                    PruningLogEntry(
                        depth=depth,
                        side="pro",
                        action_description=arg.claim[:50] + "...",
                        cut_type="beta",
                        value=v,
                        alpha=alpha,
                        beta=beta,
                    )
                )
                break
        return v

    def _minimax_min(
        self, state: DebateState, depth: int, alpha: float, beta: float
    ) -> float:
        if depth <= 0 or state.round_number >= state.max_rounds:
            return eval_state(state, self.belief_model, Side.PRO)
        candidates = self.arg_gen.generate_arguments(
            Side.CON,
            state.topic,
            state.pro_claims,
            state.con_claims,
            state.history,
            count=4,
        )
        if not candidates:
            return eval_state(state, self.belief_model, Side.PRO)
        v = float("inf")
        for arg in candidates:
            child = apply_move(state, Side.CON, arg, self.belief_model)
            v = min(v, self._minimax_max(child, depth - 1, alpha, beta))
            beta = min(beta, v)
            if beta <= alpha:
                self.pruning_log.append(
                    PruningLogEntry(
                        depth=depth,
                        side="con",
                        action_description=arg.claim[:50] + "...",
                        cut_type="alpha",
                        value=v,
                        alpha=alpha,
                        beta=beta,
                    )
                )
                break
        return v

    def get_pruning_log_dict(self) -> list[dict]:
        return [
            {
                "depth": e.depth,
                "side": e.side,
                "action_description": e.action_description,
                "cut_type": e.cut_type,
                "value": e.value,
                "alpha": e.alpha,
                "beta": e.beta,
            }
            for e in self.pruning_log
        ]
