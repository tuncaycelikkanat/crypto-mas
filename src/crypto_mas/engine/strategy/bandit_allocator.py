import math
from dataclasses import dataclass, field
import numpy as np


@dataclass
class TacticArmStats:
    tactic_name: str
    pulls: int = 0
    total_reward: float = 0.0
    wins: int = 0
    losses: int = 0
    rolling_returns: list[float] = field(default_factory=list)

    @property
    def mean_reward(self) -> float:
        if self.pulls == 0:
            return 0.0
        return self.total_reward / self.pulls

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        if total == 0:
            return 0.5
        return self.wins / total


class MultiArmedBanditAllocator:
    """
    Multi-Armed Bandit (MAB) allocator using UCB1 (Upper Confidence Bound)
    and Thompson Sampling to dynamically allocate capital weights to trading tactics
    based on live rolling profitability.
    """

    def __init__(self, tactic_names: list[str], exploration_c: float = 1.0, max_history: int = 50):
        self.exploration_c = exploration_c
        self.max_history = max_history
        self.total_rounds = 0
        self.arms: dict[str, TacticArmStats] = {
            name: TacticArmStats(tactic_name=name) for name in tactic_names
        }

    def record_outcome(self, tactic_name: str, return_pct: float) -> None:
        """
        Records the outcome of a closed trade executed by `tactic_name`.
        """
        arm = self.arms.get(tactic_name)
        if not arm:
            arm = TacticArmStats(tactic_name=tactic_name)
            self.arms[tactic_name] = arm

        # Normalized reward between -1.0 and +1.0 (clamped at ±10% return)
        reward = max(-1.0, min(return_pct / 10.0, 1.0))
        
        arm.pulls += 1
        arm.total_reward += reward
        self.total_rounds += 1

        if return_pct > 0:
            arm.wins += 1
        elif return_pct < 0:
            arm.losses += 1

        arm.rolling_returns.append(return_pct)
        if len(arm.rolling_returns) > self.max_history:
            arm.rolling_returns.pop(0)

    def calculate_ucb_scores(self) -> dict[str, float]:
        """
        Calculates UCB1 score for each tactic arm:
        UCB_i = mu_i + c * sqrt(ln(N) / n_i)
        """
        scores: dict[str, float] = {}
        t = max(1, self.total_rounds)

        for name, arm in self.arms.items():
            if arm.pulls == 0:
                # Unexplored arms get maximum priority
                scores[name] = 999.0
            else:
                exploitation = arm.mean_reward
                exploration = self.exploration_c * math.sqrt(math.log(t) / arm.pulls)
                scores[name] = exploitation + exploration

        return scores

    def get_capital_allocation_weights(self, min_weight: float = 0.10) -> dict[str, float]:
        """
        Translates bandit scores into normalized portfolio capital allocation weights (sum = 1.0).
        Ensures a minimum baseline weight for exploration.
        """
        ucb_scores = self.calculate_ucb_scores()
        
        # Softmax or positive-shifted normalization
        min_score = min(ucb_scores.values())
        shifted_scores = {name: max(score - min_score + 1.0, 0.1) for name, score in ucb_scores.items()}
        
        total_shifted = sum(shifted_scores.values())
        raw_weights = {name: val / total_shifted for name, val in shifted_scores.items()}

        # Blend with uniform baseline for robust exploration
        num_arms = len(self.arms)
        baseline = min_weight
        remaining_pool = max(0.0, 1.0 - (baseline * num_arms))

        weights: dict[str, float] = {}
        for name in self.arms:
            weights[name] = round(baseline + (raw_weights[name] * remaining_pool), 4)

        # Normalize to exactly 1.0
        total_w = sum(weights.values())
        if total_w > 0:
            weights = {k: round(v / total_w, 4) for k, v in weights.items()}

        return weights

    def sample_thompson(self) -> str:
        """
        Thompson Sampling using Beta distribution (Beta(1 + wins, 1 + losses)).
        Returns the sampled winning tactic name for exploration/exploitation.
        """
        samples: dict[str, float] = {}
        for name, arm in self.arms.items():
            alpha = 1 + arm.wins
            beta_param = 1 + arm.losses
            samples[name] = float(np.random.beta(alpha, beta_param))

        return max(samples, key=samples.get)  # type: ignore
