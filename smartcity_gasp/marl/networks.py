"""Small PyTorch networks for IPPO and MAPPO-style training.

The networks are intentionally compact so the demo can run on a laptop.  The
actor always receives a local observation.  For IPPO, the critic also receives a
local observation.  For MAPPO-style centralized training, the critic receives a
global state vector while the actor still acts from the local observation.
"""

from __future__ import annotations

from typing import Optional, Tuple

try:  # pragma: no cover - import branch depends on local environment
    import torch
    from torch import nn
    from torch.distributions import Categorical
except Exception as exc:  # pragma: no cover
    torch = None
    nn = None
    Categorical = None


class TorchNotAvailable(RuntimeError):
    """Raised when a training script is launched without PyTorch installed."""


def require_torch():
    if torch is None:
        raise TorchNotAvailable(
            "PyTorch is required for MARL training. Install torch or run the deterministic baselines."
        )
    return torch


if nn is not None:

    class ActorCritic(nn.Module):
        """Shared actor with either local or centralized critic input."""

        def __init__(self, obs_dim: int, action_dim: int, critic_dim: Optional[int] = None, hidden_dim: int = 96):
            super().__init__()
            critic_dim = critic_dim or obs_dim
            self.actor = nn.Sequential(
                nn.Linear(obs_dim, hidden_dim),
                nn.Tanh(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.Tanh(),
                nn.Linear(hidden_dim, action_dim),
            )
            self.critic = nn.Sequential(
                nn.Linear(critic_dim, hidden_dim),
                nn.Tanh(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.Tanh(),
                nn.Linear(hidden_dim, 1),
            )

        def distribution(self, obs):
            return Categorical(logits=self.actor(obs))

        def act(self, obs, critic_obs):
            dist = self.distribution(obs)
            action = dist.sample()
            logprob = dist.log_prob(action)
            value = self.critic(critic_obs).squeeze(-1)
            return action, logprob, value

        def evaluate_actions(self, obs, critic_obs, actions):
            dist = self.distribution(obs)
            logprobs = dist.log_prob(actions)
            entropy = dist.entropy()
            values = self.critic(critic_obs).squeeze(-1)
            return logprobs, entropy, values

else:  # pragma: no cover

    class ActorCritic:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise TorchNotAvailable("PyTorch is required to instantiate ActorCritic")
