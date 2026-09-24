"""Typed actions and guard decisions.

The action vocabulary is shared by every policy class (procedural, naive,
oracle, LLM).  A policy proposes a ``TypedAction``; the guard returns a
``GuardDecision``; the environment executes the (possibly transformed) action
and writes one trace record.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionType(str, Enum):
    NOOP = "noop"
    QUERY_EVIDENCE = "query_evidence"
    REQUEST_VERIFICATION = "request_verification"
    ESCALATE = "escalate"
    WRITE_MEMORY = "write_memory"

    REROUTE_TRAFFIC = "reroute_traffic"
    OPEN_BUS_LANE = "open_bus_lane"
    CHANGE_SIGNAL_PRIORITY = "change_signal_priority"
    CLOSE_ROAD = "close_road"

    DISPATCH_AMBULANCE = "dispatch_ambulance"
    RESTORE_POWER = "restore_power"
    ISOLATE_GRID_SEGMENT = "isolate_grid_segment"
    CLOSE_FLOODED_UNDERPASS = "close_flooded_underpass"
    DISPATCH_REPAIR_CREW = "dispatch_repair_crew"

    REDUCE_TRAFFIC_ZONE = "reduce_traffic_zone"
    ADD_PUBLIC_TRANSPORT_CAPACITY = "add_public_transport_capacity"
    BROADCAST_ALERT = "broadcast_alert"
    SEND_TARGETED_NOTICE = "send_targeted_notice"


COMMON_ACTIONS = [
    ActionType.NOOP,
    ActionType.QUERY_EVIDENCE,
    ActionType.REQUEST_VERIFICATION,
    ActionType.ESCALATE,
    ActionType.WRITE_MEMORY,
]


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GuardOutcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    SANITIZE = "sanitize"
    REQUEST_EVIDENCE = "request_evidence"
    ESCALATE = "escalate"
    HALT = "halt"


@dataclass
class TypedAction:
    role: str
    action_type: ActionType
    target: str = "city"
    payload: Dict[str, Any] = field(default_factory=dict)
    evidence_refs: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    needs_approval_prob: Optional[float] = None   # reported by the policy, used for the Brier score
    rationale: str = ""
    refs_source: str = "policy"                   # "policy" or "auto" (RL integer actions)

    @property
    def key(self) -> str:
        """Identity of an action for approvals: type and target."""

        return f"{self.action_type.value}@{self.target}"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["action_type"] = self.action_type.value
        data["risk_level"] = self.risk_level.value
        return data


@dataclass
class GuardDecision:
    outcome: GuardOutcome
    executed: bool
    rule_id: Optional[str] = None
    violation_type: Optional[str] = None
    attempted_violation: bool = False     # the proposal would break an active rule if executed as proposed
    reason: str = ""
    requires_approval: bool = False
    approval_granted: bool = False
    supported: bool = True                # cited evidence exists, is verified, and matches the action's topic
    approval_waived: bool = False         # an adaptive governor let a trusted role skip a soft approval
    transformed_action: Optional[TypedAction] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["outcome"] = self.outcome.value
        if self.transformed_action is not None:
            data["transformed_action"] = self.transformed_action.to_dict()
        return data
