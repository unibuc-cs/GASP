"""Typed actions used by the governed smart-city MARL prototype.

This file deliberately avoids clever abstractions.  The paper argues that
agentic systems should expose control-relevant semantics as typed records, so
this module keeps the record structure explicit: role, action type, target,
payload, evidence, risk, and escalation fields are all visible in the trace.

The reinforcement-learning layer only chooses a small integer action.  The
environment converts that integer into one of these typed actions before the
governance guard and transition function are applied.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(str, Enum):
    """Human-readable risk levels used by the governance guard."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GuardOutcome(str, Enum):
    """Possible enforcement outcomes returned by the runtime guard."""

    ALLOW = "allow"
    DENY = "deny"
    SANITIZE = "sanitize"
    REQUEST_EVIDENCE = "request_evidence"
    ESCALATE = "escalate"
    HALT = "halt"


class ActionType(str, Enum):
    """Small action vocabulary shared by deterministic and learned policies."""

    NOOP = "noop"
    QUERY_EVIDENCE = "query_evidence"
    REQUEST_VERIFICATION = "request_verification"
    ESCALATE = "escalate"
    WRITE_MEMORY = "write_memory"

    # Traffic and mobility actions.
    REROUTE_TRAFFIC = "reroute_traffic"
    OPEN_BUS_LANE = "open_bus_lane"
    CHANGE_SIGNAL_PRIORITY = "change_signal_priority"
    CLOSE_ROAD = "close_road"

    # Emergency and infrastructure actions.
    DISPATCH_AMBULANCE = "dispatch_ambulance"
    RESTORE_POWER = "restore_power"
    ISOLATE_GRID_SEGMENT = "isolate_grid_segment"
    CLOSE_FLOODED_UNDERPASS = "close_flooded_underpass"
    DISPATCH_REPAIR_CREW = "dispatch_repair_crew"

    # Environment, transport, and communication actions.
    REDUCE_TRAFFIC_ZONE = "reduce_traffic_zone"
    ADD_PUBLIC_TRANSPORT_CAPACITY = "add_public_transport_capacity"
    BROADCAST_ALERT = "broadcast_alert"
    SEND_TARGETED_NOTICE = "send_targeted_notice"


# The learning interface uses a compact shared discrete action space.  Some
# indices map to role-specific actions inside the environment.
ACTION_INDEX_TO_KIND = {
    0: "NOOP",
    1: "QUERY_EVIDENCE",
    2: "REQUEST_VERIFICATION",
    3: "ESCALATE",
    4: "WRITE_MEMORY",
    5: "ROLE_ACTION_1",
    6: "ROLE_ACTION_2",
    7: "ROLE_ACTION_3",
}

ACTION_DIM = len(ACTION_INDEX_TO_KIND)


@dataclass
class TypedAction:
    """Structured action proposed by a role policy.

    Parameters
    ----------
    role:
        Name of the agent or role issuing the action.
    action_type:
        Control-relevant action type.  The environment and guard only reason
        over this explicit field, not over free-form natural language.
    target:
        Symbolic target, such as a route, district, road segment, or citizen
        channel.
    payload:
        Optional action parameters.  This is where natural-language summaries
        or domain-specific values can live without becoming the control layer.
    evidence_refs:
        References to evidence items visible in the trace.
    risk_level:
        Risk level assigned before guard evaluation.
    escalation_requested:
        Whether the agent itself requested escalation.
    p_escalation:
        A simple pre-guard probability estimate used by EscCE.  Learned agents
        could eventually output this directly; the current prototype estimates
        it from action type and risk level.
    """

    role: str
    action_type: ActionType
    target: str = "city"
    payload: Dict[str, Any] = field(default_factory=dict)
    evidence_refs: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    escalation_requested: bool = False
    p_escalation: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["action_type"] = self.action_type.value
        data["risk_level"] = self.risk_level.value
        return data


@dataclass
class GuardDecision:
    """Decision returned by the runtime guard for one typed action."""

    outcome: GuardOutcome
    executed: bool
    violation_type: Optional[str] = None
    reason: str = ""
    requires_escalation: bool = False
    supported: bool = True
    transformed_action: Optional[TypedAction] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["outcome"] = self.outcome.value
        if self.transformed_action is not None:
            data["transformed_action"] = self.transformed_action.to_dict()
        return data
