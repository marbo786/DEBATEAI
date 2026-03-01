"""
Probabilistic audience model: belief update from argument strengths.
Simple weighted/Bayesian-style update, clamped to [0, 1].
"""
from .state import Argument, Side


class BeliefModel:
    """
    Updates audience belief (probability of favoring Pro) from argument strengths.
    Demonstrates probabilistic reasoning: each round evidence shifts belief.
    """

    def __init__(self, sensitivity: float = 0.12, prior: float = 0.5):
        """
        sensitivity: how much one round can move belief (scale of delta).
        prior: initial belief (default 0.5).
        """
        self.sensitivity = sensitivity
        self.prior = prior

    def update(
        self,
        current_belief: float,
        pro_strength: float,
        con_strength: float,
    ) -> float:
        """
        One round update. Positive pro_strength pushes belief up, con_strength down.
        Simplified Bayesian-style: treat strength difference as evidence magnitude.
        """
        delta = self.sensitivity * (pro_strength - con_strength)
        new_belief = current_belief + delta
        return max(0.0, min(1.0, new_belief))

    def update_from_arguments(
        self,
        current_belief: float,
        pro_argument: Argument | None,
        con_argument: Argument | None,
    ) -> float:
        """
        Convenience: compute strengths from this round's arguments and update.
        If only one side spoke (e.g. first move), the other strength is 0.
        """
        pro_s = pro_argument.strength if pro_argument else 0.0
        con_s = con_argument.strength if con_argument else 0.0
        return self.update(current_belief, pro_s, con_s)
