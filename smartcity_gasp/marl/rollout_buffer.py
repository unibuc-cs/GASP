"""Rollout storage used by the compact PPO trainers.

The buffer stores flattened per-agent transitions.  This keeps IPPO and MAPPO
implementation short: IPPO fills ``critic_obs`` with local observations, while
MAPPO fills it with the centralized global state vector.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np


@dataclass
class RolloutBuffer:
    obs: List[np.ndarray] = field(default_factory=list)
    critic_obs: List[np.ndarray] = field(default_factory=list)
    actions: List[int] = field(default_factory=list)
    logprobs: List[float] = field(default_factory=list)
    rewards: List[float] = field(default_factory=list)
    dones: List[float] = field(default_factory=list)
    values: List[float] = field(default_factory=list)

    def clear(self) -> None:
        self.obs.clear()
        self.critic_obs.clear()
        self.actions.clear()
        self.logprobs.clear()
        self.rewards.clear()
        self.dones.clear()
        self.values.clear()

    def __len__(self) -> int:
        return len(self.actions)

    def compute_returns_and_advantages(self, gamma: float = 0.99, lam: float = 0.95):
        values = np.asarray(self.values + [0.0], dtype=np.float32)
        rewards = np.asarray(self.rewards, dtype=np.float32)
        dones = np.asarray(self.dones, dtype=np.float32)
        advantages = np.zeros_like(rewards, dtype=np.float32)
        gae = 0.0
        for t in reversed(range(len(rewards))):
            nonterminal = 1.0 - dones[t]
            delta = rewards[t] + gamma * values[t + 1] * nonterminal - values[t]
            gae = delta + gamma * lam * nonterminal * gae
            advantages[t] = gae
        returns = advantages + np.asarray(self.values, dtype=np.float32)
        return returns, advantages
