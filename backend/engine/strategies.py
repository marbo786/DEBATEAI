"""Strategy abstractions for selecting debate moves."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

from .belief import BeliefModel
from .minimax import MinimaxAgent, apply_move, eval_state
from .reasoning import ArgumentGenerator
from .state import Argument, DebateState, Side


class DebateStrategy(Protocol):
    """Protocol for selecting the next argument for a side."""

    strategy_id: str
    display_name: str

    def propose_move(self, state: DebateState, side: Side) -> tuple[Argument | None, float]:
        """Return the selected argument and a strategy score."""

    def explain_decision(self) -> dict:
        """Return metadata about the last strategy decision."""


@dataclass
class _BaseStrategy:
    strategy_id: str
    display_name: str
    arg_gen: ArgumentGenerator
    belief_model: BeliefModel

    def __post_init__(self) -> None:
        self._last_explanation: dict = {}

    def explain_decision(self) -> dict:
        return self._last_explanation


class MinimaxStrategy(_BaseStrategy):
    """Adapter around the existing alpha-beta minimax agent."""

    def __init__(self, arg_gen: ArgumentGenerator, belief_model: BeliefModel, depth: int = 3):
        super().__init__(
            strategy_id="minimax",
            display_name="Minimax (alpha-beta)",
            arg_gen=arg_gen,
            belief_model=belief_model,
        )
        self.agent = MinimaxAgent(argument_generator=arg_gen, belief_model=belief_model, depth=depth)

    def propose_move(self, state: DebateState, side: Side) -> tuple[Argument | None, float]:
        best, score = self.agent.get_best_argument(state, side)
        self._last_explanation = {
            "strategy": self.strategy_id,
            "score": score,
            "search_depth": self.agent.depth,
            "pruning_log": self.agent.get_pruning_log_dict(),
        }
        return best, score


class MonteCarloRolloutStrategy(_BaseStrategy):
    """Evaluate each candidate by random rollout simulations."""

    def __init__(
        self,
        arg_gen: ArgumentGenerator,
        belief_model: BeliefModel,
        rollouts_per_move: int = 12,
        rollout_depth: int = 4,
        seed: int | None = None,
    ):
        super().__init__(
            strategy_id="mcts",
            display_name="Monte Carlo Rollout",
            arg_gen=arg_gen,
            belief_model=belief_model,
        )
        self.rollouts_per_move = rollouts_per_move
        self.rollout_depth = rollout_depth
        self._rng = random.Random(seed)

    def _utility(self, base_belief: float, final_belief: float, side: Side) -> float:
        return (final_belief - base_belief) if side == Side.PRO else (base_belief - final_belief)

    def _simulate(self, state: DebateState, next_side: Side, steps: int) -> DebateState:
        sim_state = state
        side = next_side
        for _ in range(steps):
            if sim_state.round_number >= sim_state.max_rounds * 2:
                break
            candidates = self.arg_gen.generate_arguments(
                side=side,
                topic=sim_state.topic,
                pro_claims=sim_state.pro_claims,
                con_claims=sim_state.con_claims,
                history=sim_state.history,
                count=4,
            )
            if not candidates:
                break
            sim_state = apply_move(sim_state, side, self._rng.choice(candidates), self.belief_model)
            side = Side.CON if side == Side.PRO else Side.PRO
        return sim_state

    def propose_move(self, state: DebateState, side: Side) -> tuple[Argument | None, float]:
        candidates = self.arg_gen.generate_arguments(
            side=side,
            topic=state.topic,
            pro_claims=state.pro_claims,
            con_claims=state.con_claims,
            history=state.history,
            count=6,
        )
        if not candidates:
            return None, 0.0

        best_arg = candidates[0]
        best_value = -float("inf")
        scores: list[float] = []
        for candidate in candidates:
            first_state = apply_move(state, side, candidate, self.belief_model)
            next_side = Side.CON if side == Side.PRO else Side.PRO
            total = 0.0
            for _ in range(self.rollouts_per_move):
                final_state = self._simulate(first_state, next_side, self.rollout_depth)
                total += self._utility(state.belief, final_state.belief, side)
            expected_delta = total / self.rollouts_per_move
            scores.append(expected_delta)
            if expected_delta > best_value:
                best_value = expected_delta
                best_arg = candidate

        self._last_explanation = {
            "strategy": self.strategy_id,
            "rollouts_per_move": self.rollouts_per_move,
            "rollout_depth": self.rollout_depth,
            "candidate_count": len(candidates),
            "expected_belief_delta": best_value,
        }
        return best_arg, best_value


class BeamSearchStrategy(_BaseStrategy):
    """Breadth-limited exploration with heuristic ranking."""

    def __init__(
        self,
        arg_gen: ArgumentGenerator,
        belief_model: BeliefModel,
        beam_width: int = 3,
        depth: int = 3,
    ):
        super().__init__(
            strategy_id="beam",
            display_name="Beam Search",
            arg_gen=arg_gen,
            belief_model=belief_model,
        )
        self.beam_width = beam_width
        self.depth = depth

    def _rank_for_side(self, state: DebateState, side: Side) -> float:
        pro_score = eval_state(state, self.belief_model, Side.PRO)
        return pro_score if side == Side.PRO else (1.0 - pro_score)

    def propose_move(self, state: DebateState, side: Side) -> tuple[Argument | None, float]:
        roots = self.arg_gen.generate_arguments(
            side=side,
            topic=state.topic,
            pro_claims=state.pro_claims,
            con_claims=state.con_claims,
            history=state.history,
            count=max(6, self.beam_width * 2),
        )
        if not roots:
            return None, 0.0

        best_arg = roots[0]
        best_score = -float("inf")

        for root in roots:
            first_state = apply_move(state, side, root, self.belief_model)
            beam = [first_state]
            current_side = Side.CON if side == Side.PRO else Side.PRO

            for _ in range(self.depth - 1):
                expanded: list[DebateState] = []
                for node in beam:
                    candidates = self.arg_gen.generate_arguments(
                        side=current_side,
                        topic=node.topic,
                        pro_claims=node.pro_claims,
                        con_claims=node.con_claims,
                        history=node.history,
                        count=self.beam_width,
                    )
                    for candidate in candidates:
                        expanded.append(apply_move(node, current_side, candidate, self.belief_model))
                if not expanded:
                    break
                expanded.sort(key=lambda s: self._rank_for_side(s, side), reverse=True)
                beam = expanded[: self.beam_width]
                current_side = Side.CON if current_side == Side.PRO else Side.PRO

            root_score = max(self._rank_for_side(node, side) for node in beam)
            if root_score > best_score:
                best_score = root_score
                best_arg = root

        self._last_explanation = {
            "strategy": self.strategy_id,
            "beam_width": self.beam_width,
            "search_depth": self.depth,
            "candidate_count": len(roots),
            "heuristic_score": best_score,
        }
        return best_arg, best_score


def build_strategy(
    strategy: str | DebateStrategy | None,
    arg_gen: ArgumentGenerator,
    belief_model: BeliefModel,
    seed: int | None = None,
) -> DebateStrategy:
    """Create a strategy instance from a strategy id or return the supplied strategy."""
    if strategy is None:
        strategy = "minimax"
    if hasattr(strategy, "propose_move") and hasattr(strategy, "strategy_id"):
        return strategy

    strategy_id = str(strategy).lower()
    if strategy_id == "minimax":
        return MinimaxStrategy(arg_gen, belief_model)
    if strategy_id == "mcts":
        return MonteCarloRolloutStrategy(arg_gen, belief_model, seed=seed)
    if strategy_id == "beam":
        return BeamSearchStrategy(arg_gen, belief_model)
    raise ValueError(f"unknown strategy '{strategy}'")
