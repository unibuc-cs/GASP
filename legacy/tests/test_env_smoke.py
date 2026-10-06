"""Smoke tests for the SmartCity-GASP-MARL artifact.

Run with:
    python tests/test_env_smoke.py

The tests avoid pytest so the artifact remains dependency-light.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smartcity_gasp.core.metrics import aggregate_by_mode
from smartcity_gasp.envs.smartcity_parallel_env import EnvConfig, SmartCityParallelEnv
from smartcity_gasp.policies.rule_based import RuleBasedPolicy


def test_env_runs_one_episode() -> None:
    env = SmartCityParallelEnv(EnvConfig(governed=True, activation_mode="scenario", seed=123))
    policy = RuleBasedPolicy()
    env.reset()
    done = False
    while not done:
        _, _, terms, truncs, _ = env.step(policy.act(env))
        done = all(terms.values()) or all(truncs.values())
    assert env.last_summary is not None
    assert len(env.last_summary.records) > 0


def test_metrics_are_computed() -> None:
    env = SmartCityParallelEnv(EnvConfig(governed=False, activation_mode="scenario", seed=123))
    policy = RuleBasedPolicy()
    summaries = []
    for _ in range(3):
        env.reset()
        done = False
        while not done:
            _, _, terms, truncs, _ = env.step(policy.act(env))
            done = all(terms.values()) or all(truncs.values())
        assert env.last_summary is not None
        env.last_summary.mode = "test"
        summaries.append(env.last_summary)
    rows = aggregate_by_mode(summaries)
    assert len(rows) == 1
    assert rows[0].episodes == 3


if __name__ == "__main__":
    test_env_runs_one_episode()
    test_metrics_are_computed()
    print("All smoke tests passed.")
