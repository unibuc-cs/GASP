"""Domain interface.

A domain supplies the roles, the action catalogue, the scenario sampler, the
evidence pool, the effects of actions, and the success condition.  Everything
else (guard, traces, metrics, statistics, policies) is shared.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

from .actions import ActionType, RiskLevel, TypedAction
from .evidence import Evidence


@dataclass
class ActionSpec:
    action_type: ActionType
    risk: RiskLevel
    high_impact: bool
    evidence_topics: Tuple[str, ...] = ()   # topics whose verified evidence supports the action; empty = none needed
    public: bool = False                    # public communication rule applies
    description: str = ""


@dataclass
class Scenario:
    scenario_id: str
    family: str
    severity: int                      # 1..3
    evidence_quality: str              # missing, partial, complete, conflicting
    overseer_available: bool
    overseer_latency: int              # steps until an approval request is answered
    false_report: bool                 # an untrue report is planted in the evidence pool
    distractor: bool                   # unrelated low-severity evidence is planted
    max_steps: int
    required_roles: List[str]
    target: str                        # main district or route
    params: Dict[str, Any] = field(default_factory=dict)   # domain fields: congestion, hospital_access_risk, ...

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Domain(Protocol):
    name: str
    service_roles: List[str]
    role_actions: Dict[str, List[ActionType]]
    action_specs: Dict[ActionType, ActionSpec]
    outcome_flags: List[str]

    def families(self) -> List[str]: ...
    def sample_scenario(self, rng: random.Random, family: str, index: int, options: Dict[str, Any]) -> Scenario: ...
    def build_evidence(self, scenario: Scenario) -> List[Evidence]: ...
    def is_success(self, state: "State") -> bool: ...
    def apply(self, state: "State", action: TypedAction, supported: bool, cited_false: bool) -> float: ...
    def requires_approval(self, state: "State", action: TypedAction, cfg: Dict[str, Any]) -> bool: ...
    def sanitize(self, state: "State", action: TypedAction, rules: Any): ...
    def default_payload(self, state: "State", action_type: ActionType) -> Dict[str, Any]: ...
    def discover_evidence(self, state: "State", role: str, topic: str) -> List[Evidence]: ...
    def flags_visible_to(self, role: str) -> List[str]: ...


# Imported late to avoid a cycle in type checkers.
from .state import State  # noqa: E402  (re-exported for domains)
