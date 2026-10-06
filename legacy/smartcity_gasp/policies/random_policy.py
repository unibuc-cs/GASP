"""Random policy used for smoke tests and untrained MARL baselines."""

from __future__ import annotations

import random
from typing import Dict

from smartcity_gasp.core.actions import ACTION_DIM
from smartcity_gasp.envs.smartcity_parallel_env import SmartCityParallelEnv


class RandomPolicy:
    def __init__(self, seed: int = 7):
        self.rng = random.Random(seed)

    def act(self, env: SmartCityParallelEnv) -> Dict[str, int]:
        return {agent: self.rng.randrange(ACTION_DIM) for agent in env.agents}
