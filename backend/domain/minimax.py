"""
Adversarial search: Minimax with Alpha-Beta pruning.
Pro maximizes belief impact, Con minimizes. Depth 2-3, pruning logged.

Phase 2 enhancements:
- get_best_argument accepts optional LLM-generated extra_candidates
- eval_state includes momentum, rebuttal, and diversity bonuses
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

    Combines:
    - Current belief (core signal)
    - Last argument strength bonus/penalty
    - Momentum: consecutive moves favouring same side (+0.05)
    - Rebuttal bonus: attacking opponent's claim directly (+0.04)
    - Diversity bonus: using a reasoning type not seen in last 2 same-side moves (+0.03)
    """
    score = state.belief  # 0..1, Pro wants to maximize

    if not state.history:
        return score

    last = state.history[-1]

    # Last argument strength signal
    if last.side == Side.PRO:
        score += 0.1 * last.argument.strength
    else:
        score -= 0.1 * last.argument.strength

    # --- Momentum bonus ---
    # If the last 2 moves both shifted belief in the same direction, reward momentum
    if len(state.belief_history) >= 3:
        delta1 = state.belief_history[-1] - state.belief_history[-2]
        delta2 = state.belief_history[-2] - state.belief_history[-3]
        if delta1 > 0 and delta2 > 0:
            score += 0.05  # Pro has momentum
        elif delta1 < 0 and delta2 < 0:
            score -= 0.05  # Con has momentum

    # --- Rebuttal bonus ---
    # Arguments that directly attack the opponent get a small bonus for strategic value
    if last.argument.attack_target is not None:
        if last.side == Side.PRO:
            score += 0.04
        else:
            score -= 0.04

    # --- Diversity bonus ---
    # Using a reasoning type not seen in the last 2 same-side moves keeps debate varied
    same_side_recent = [
        r.argument.reasoning_type
        for r in state.history[-4:]
        if r.side == last.side
    ][-2:]  # last 2 moves for that side

    if len(same_side_recent) >= 1 and last.argument.reasoning_type not in same_side_recent[:-1]:
        if last.side == Side.PRO:
            score += 0.03
        else:
            score -= 0.03

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

    Phase 2: accepts optional LLM-generated extra_candidates at root level.
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
        extra_candidates: list[Argument] | None = None,
    ) -> tuple[Argument | None, float]:
        """
        Returns (best argument, value). Uses alpha-beta; fills pruning_log.

        Args:
            state: Current debate state.
            side: Which side is moving (PRO or CON).
            extra_candidates: Optional LLM-generated arguments to add to the
                candidate pool at the root level. These are evaluated by minimax
                alongside template-generated candidates.
        """
        self.pruning_log.clear()
        template_candidates = self.arg_gen.generate_arguments(
            side=side,
            topic=state.topic,
            pro_claims=state.pro_claims,
            con_claims=state.con_claims,
            history=state.history,
            count=6,
            used_claims=state.used_claims,
        )

        # Merge LLM candidates into the pool (deduplicate by claim text)
        if extra_candidates:
            existing_claims = {a.claim for a in template_candidates}
            for llm_arg in extra_candidates:
                if llm_arg.claim not in existing_claims:
                    template_candidates.append(llm_arg)
                    existing_claims.add(llm_arg.claim)

        candidates = template_candidates
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
        if depth <= 0 or self._is_terminal(state):
            return eval_state(state, self.belief_model, Side.PRO)
        candidates = self.arg_gen.generate_arguments(
            Side.PRO,
            state.topic,
            state.pro_claims,
            state.con_claims,
            state.history,
            count=4,
            used_claims=state.used_claims,
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
        if depth <= 0 or self._is_terminal(state):
            return eval_state(state, self.belief_model, Side.PRO)
        candidates = self.arg_gen.generate_arguments(
            Side.CON,
            state.topic,
            state.pro_claims,
            state.con_claims,
            state.history,
            count=4,
            used_claims=state.used_claims,
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

    @staticmethod
    def _is_terminal(state: DebateState) -> bool:
        """Terminal when the configured number of full rounds has been played."""
        return state.round_number >= (state.max_rounds * 2)
