"""Compact IPPO and MAPPO-style PPO trainers.

This is a research-demo implementation, not a high-performance RL library.  The
trainer is intentionally small so that reviewers and students can read it.  It
supports two modes:

* ``ippo``: actor and critic both use local observations;
* ``mappo``: actor uses local observations, critic uses the global city state.

Both modes emit the same integer actions and therefore produce the same typed
trace structure when executed in ``SmartCityParallelEnv``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from smartcity_gasp.core.metrics import EpisodeSummary, aggregate_by_mode
from smartcity_gasp.envs.smartcity_parallel_env import EnvConfig, SmartCityParallelEnv
from smartcity_gasp.marl.networks import ActorCritic, require_torch
from smartcity_gasp.marl.rollout_buffer import RolloutBuffer


@dataclass
class PPOConfig:
    algorithm: str = "mappo"  # ippo or mappo
    episodes: int = 200
    update_every: int = 20
    ppo_epochs: int = 4
    gamma: float = 0.98
    gae_lambda: float = 0.95
    clip_eps: float = 0.20
    lr: float = 3e-4
    entropy_coef: float = 0.01
    value_coef: float = 0.50
    hidden_dim: int = 96
    seed: int = 7


class PPOTrainer:
    """Single shared actor with local or centralized critic."""

    def __init__(self, env: SmartCityParallelEnv, config: PPOConfig):
        self.torch = require_torch()
        self.env = env
        self.config = config
        self.torch.manual_seed(config.seed)
        np.random.seed(config.seed)

        obs_dim = env.observation_dim
        critic_dim = env.global_observation_dim if config.algorithm == "mappo" else obs_dim
        self.model = ActorCritic(obs_dim, env.action_dim, critic_dim=critic_dim, hidden_dim=config.hidden_dim)
        self.optimizer = self.torch.optim.Adam(self.model.parameters(), lr=config.lr)
        self.buffer = RolloutBuffer()
        self.train_summaries: List[EpisodeSummary] = []

    def train(self) -> List[EpisodeSummary]:
        """Run PPO training and return episode summaries."""

        for ep in range(1, self.config.episodes + 1):
            summary = self._collect_episode()
            self.train_summaries.append(summary)
            if len(self.buffer) > 0 and ep % self.config.update_every == 0:
                self._update()
                self.buffer.clear()
        if len(self.buffer) > 0:
            self._update()
            self.buffer.clear()
        return self.train_summaries

    def evaluate(self, episodes: int = 40, deterministic: bool = True) -> List[EpisodeSummary]:
        """Evaluate the trained policy without updating it."""

        summaries: List[EpisodeSummary] = []
        self.model.eval()
        with self.torch.no_grad():
            for _ in range(episodes):
                obs, _ = self.env.reset()
                done = False
                while not done:
                    action_dict: Dict[str, int] = {}
                    global_obs = self.env.global_state_vector()
                    for agent, agent_obs in obs.items():
                        obs_t = self.torch.tensor(agent_obs, dtype=self.torch.float32).unsqueeze(0)
                        critic_obs = global_obs if self.config.algorithm == "mappo" else agent_obs
                        critic_t = self.torch.tensor(critic_obs, dtype=self.torch.float32).unsqueeze(0)
                        dist = self.model.distribution(obs_t)
                        if deterministic:
                            action = int(self.torch.argmax(dist.logits, dim=-1).item())
                        else:
                            action = int(dist.sample().item())
                        action_dict[agent] = action
                    obs, rewards, terms, truncs, _ = self.env.step(action_dict)
                    done = all(terms.values()) or all(truncs.values())
                if self.env.last_summary is not None:
                    self.env.last_summary.mode = self._mode_label()
                    summaries.append(self.env.last_summary)
        self.model.train()
        return summaries

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.torch.save({"model": self.model.state_dict(), "config": self.config.__dict__}, path)

    def load(self, path: str | Path) -> None:
        payload = self.torch.load(path, map_location="cpu")
        self.model.load_state_dict(payload["model"])

    def _mode_label(self) -> str:
        guard = "governed" if self.env.config.governed else "unguarded"
        return f"{self.config.algorithm.upper()}_{guard}"

    def _collect_episode(self) -> EpisodeSummary:
        obs, _ = self.env.reset()
        done = False
        while not done:
            global_obs = self.env.global_state_vector()
            action_dict: Dict[str, int] = {}
            transition_cache = []
            for agent, agent_obs in obs.items():
                critic_obs = global_obs if self.config.algorithm == "mappo" else agent_obs
                obs_t = self.torch.tensor(agent_obs, dtype=self.torch.float32).unsqueeze(0)
                critic_t = self.torch.tensor(critic_obs, dtype=self.torch.float32).unsqueeze(0)
                action_t, logprob_t, value_t = self.model.act(obs_t, critic_t)
                action = int(action_t.item())
                action_dict[agent] = action
                transition_cache.append((agent_obs, critic_obs, action, float(logprob_t.item()), float(value_t.item())))

            next_obs, rewards, terms, truncs, _ = self.env.step(action_dict)
            done = all(terms.values()) or all(truncs.values())
            for agent, (agent_obs, critic_obs, action, logprob, value) in zip(obs.keys(), transition_cache):
                self.buffer.obs.append(np.asarray(agent_obs, dtype=np.float32))
                self.buffer.critic_obs.append(np.asarray(critic_obs, dtype=np.float32))
                self.buffer.actions.append(action)
                self.buffer.logprobs.append(logprob)
                self.buffer.rewards.append(float(rewards[agent]))
                self.buffer.dones.append(1.0 if done else 0.0)
                self.buffer.values.append(value)
            obs = next_obs
        assert self.env.last_summary is not None
        self.env.last_summary.mode = self._mode_label()
        return self.env.last_summary

    def _update(self) -> None:
        returns, advantages = self.buffer.compute_returns_and_advantages(
            gamma=self.config.gamma,
            lam=self.config.gae_lambda,
        )
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        torch = self.torch
        obs = torch.tensor(np.asarray(self.buffer.obs), dtype=torch.float32)
        critic_obs = torch.tensor(np.asarray(self.buffer.critic_obs), dtype=torch.float32)
        actions = torch.tensor(np.asarray(self.buffer.actions), dtype=torch.long)
        old_logprobs = torch.tensor(np.asarray(self.buffer.logprobs), dtype=torch.float32)
        returns_t = torch.tensor(returns, dtype=torch.float32)
        advantages_t = torch.tensor(advantages, dtype=torch.float32)

        n = len(actions)
        batch_size = min(256, n)
        for _ in range(self.config.ppo_epochs):
            perm = torch.randperm(n)
            for start in range(0, n, batch_size):
                idx = perm[start:start + batch_size]
                logprobs, entropy, values = self.model.evaluate_actions(obs[idx], critic_obs[idx], actions[idx])
                ratio = torch.exp(logprobs - old_logprobs[idx])
                surrogate_1 = ratio * advantages_t[idx]
                surrogate_2 = torch.clamp(ratio, 1.0 - self.config.clip_eps, 1.0 + self.config.clip_eps) * advantages_t[idx]
                policy_loss = -torch.min(surrogate_1, surrogate_2).mean()
                value_loss = (returns_t[idx] - values).pow(2).mean()
                entropy_loss = -entropy.mean()
                loss = policy_loss + self.config.value_coef * value_loss + self.config.entropy_coef * entropy_loss

                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()


def save_training_curve(summaries: List[EpisodeSummary], path: str | Path) -> None:
    """Write per-episode summaries to CSV for plotting."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["episode", "mode", "scenario_type", "success", "steps", "total_reward"])
        writer.writeheader()
        for idx, summary in enumerate(summaries, start=1):
            writer.writerow({
                "episode": idx,
                "mode": summary.mode,
                "scenario_type": summary.scenario_type,
                "success": int(summary.success),
                "steps": summary.steps,
                "total_reward": round(summary.total_reward, 4),
            })
