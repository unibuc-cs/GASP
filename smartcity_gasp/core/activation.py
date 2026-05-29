"""Scenario-based role activation.

The paper separates two questions: which roles should participate, and how
proposed actions should be governed.  This module implements the first question.
The same activation policy can be used with or without the governance guard,
which allows the evaluation to isolate the effect of runtime governance.
"""

from __future__ import annotations

from typing import List

from .state import SERVICE_AGENTS, Scenario


def required_agents_for_scenario(scenario: Scenario) -> List[str]:
    """Return the role set expected to be relevant for the scenario."""

    return list(scenario.required_services)


def activate_agents(scenario: Scenario, mode: str = "scenario") -> List[str]:
    """Select active service roles for one episode.

    Parameters
    ----------
    scenario:
        Incident description.
    mode:
        ``"scenario"`` activates only relevant roles. ``"all"`` activates all
        service roles. ``"direct"`` uses a single direct controller role.
    """

    if mode == "direct":
        return ["DirectController"]
    if mode == "all":
        return list(SERVICE_AGENTS)
    if mode == "scenario":
        return required_agents_for_scenario(scenario)
    raise ValueError(f"unknown activation mode: {mode}")
