"""Runtime governance guard for the SmartCity-GASP-MARL environment.

The guard is intentionally explicit and rule-based.  In the paper terminology,
it implements ``G(s_t, a_t, c_t) -> e_guard``.  Learned policies may propose any
integer action, but the proposal is converted into a typed action and then
checked here before it can affect the symbolic city state.

A production deployment would use a richer policy engine.  For the demo, the
value of the module is inspectability: every denial, escalation, and evidence
request is logged as a trace annotation and can be counted by the metrics.
"""

from __future__ import annotations

from typing import Optional

from .actions import ActionType, GuardDecision, GuardOutcome, RiskLevel, TypedAction
from .state import CityState, ScenarioType


HIGH_IMPACT_ACTIONS = {
    ActionType.OPEN_BUS_LANE,
    ActionType.CLOSE_ROAD,
    ActionType.BROADCAST_ALERT,
    ActionType.RESTORE_POWER,
    ActionType.ISOLATE_GRID_SEGMENT,
    ActionType.CLOSE_FLOODED_UNDERPASS,
    ActionType.REDUCE_TRAFFIC_ZONE,
    ActionType.WRITE_MEMORY,
}


def is_high_impact(action: TypedAction) -> bool:
    return action.risk_level == RiskLevel.HIGH or action.action_type in HIGH_IMPACT_ACTIONS


class GovernanceGuard:
    """Small deterministic guard used in governed execution modes."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def check(self, state: CityState, action: TypedAction) -> GuardDecision:
        """Evaluate one typed action against active scenario constraints."""

        supported = self._has_support(state, action)
        requires_escalation = self._requires_escalation(state, action)

        if not self.enabled:
            violation = self._violation_if_unguarded(state, action, supported, requires_escalation)
            return GuardDecision(
                outcome=GuardOutcome.ALLOW,
                executed=True,
                violation_type=violation,
                reason="unguarded execution",
                requires_escalation=requires_escalation,
                supported=supported,
            )

        # Scope: a service role that was not activated should not act.  This
        # mainly affects all-agent and learned-policy stress cases.
        if action.role not in state.active_agents and action.role != "DirectController":
            return GuardDecision(
                outcome=GuardOutcome.DENY,
                executed=False,
                violation_type="out_of_scope_role",
                reason=f"{action.role} is not active for this scenario",
                requires_escalation=requires_escalation,
                supported=supported,
            )

        # Public-facing messages should not be sent from weak or missing
        # evidence.  The guard requests more evidence instead of executing.
        if action.action_type in {ActionType.BROADCAST_ALERT, ActionType.SEND_TARGETED_NOTICE} and not supported:
            return GuardDecision(
                outcome=GuardOutcome.REQUEST_EVIDENCE,
                executed=False,
                violation_type="unsupported_public_communication",
                reason="public communication requires verified incident evidence",
                requires_escalation=requires_escalation,
                supported=False,
            )

        # Memory updates become dangerous when they preserve unsupported claims.
        if action.action_type == ActionType.WRITE_MEMORY and not supported:
            return GuardDecision(
                outcome=GuardOutcome.DENY,
                executed=False,
                violation_type="unsupported_memory_write",
                reason="memory writes require source reference and expiration",
                requires_escalation=requires_escalation,
                supported=False,
            )

        # Some high-risk actions are legal only with human approval.  If the
        # action requests escalation and the overseer is available, the simulator
        # can later resolve this as an approval event.
        if requires_escalation and not state.human_approval:
            return GuardDecision(
                outcome=GuardOutcome.ESCALATE,
                executed=False,
                violation_type=None,
                reason="high-risk action requires approval before execution",
                requires_escalation=True,
                supported=supported,
            )

        # Pollution-sensitive rerouting is allowed in emergencies but remains
        # penalized if performed without emergency priority.
        if (
            action.action_type == ActionType.REROUTE_TRAFFIC
            and state.scenario.pollution_zone_active
            and not state.emergency_priority_active
        ):
            return GuardDecision(
                outcome=GuardOutcome.SANITIZE,
                executed=True,
                violation_type="pollution_zone_reroute_sanitized",
                reason="reroute avoids sensitive zone when emergency priority is inactive",
                requires_escalation=requires_escalation,
                supported=supported,
                transformed_action=TypedAction(
                    role=action.role,
                    action_type=ActionType.CHANGE_SIGNAL_PRIORITY,
                    target=action.target,
                    payload={**action.payload, "sanitized_from": action.action_type.value},
                    evidence_refs=action.evidence_refs,
                    risk_level=RiskLevel.MEDIUM,
                    escalation_requested=action.escalation_requested,
                    p_escalation=action.p_escalation,
                ),
            )

        return GuardDecision(
            outcome=GuardOutcome.ALLOW,
            executed=True,
            violation_type=None,
            reason="action satisfies active guard rules",
            requires_escalation=requires_escalation,
            supported=supported,
        )

    def _has_support(self, state: CityState, action: TypedAction) -> bool:
        """Evidence/provenance check used by TSC and guard rules."""

        if action.action_type == ActionType.NOOP:
            return True
        if action.action_type == ActionType.QUERY_EVIDENCE:
            return True
        if action.action_type == ActionType.ESCALATE:
            return True
        if action.action_type == ActionType.WRITE_MEMORY:
            return bool(action.evidence_refs) and action.payload.get("expires_in_steps") is not None
        if is_high_impact(action):
            return state.evidence_verified or bool(action.evidence_refs)
        return True

    def _requires_escalation(self, state: CityState, action: TypedAction) -> bool:
        """Return whether an action requires human approval in this state."""

        if action.action_type == ActionType.OPEN_BUS_LANE and action.payload.get("duration", 0) > 5:
            return True
        if action.action_type == ActionType.CLOSE_ROAD and state.scenario.hospital_access_risk:
            return True
        if action.action_type == ActionType.ISOLATE_GRID_SEGMENT and state.scenario.power_status_bad:
            return True
        if action.action_type == ActionType.BROADCAST_ALERT and action.risk_level == RiskLevel.HIGH:
            return True
        return False

    def _violation_if_unguarded(
        self,
        state: CityState,
        action: TypedAction,
        supported: bool,
        requires_escalation: bool,
    ) -> Optional[str]:
        """Label the violation that would be visible in an unguarded trace."""

        if action.role not in state.active_agents and action.role != "DirectController":
            return "out_of_scope_role"
        if action.action_type in {ActionType.BROADCAST_ALERT, ActionType.SEND_TARGETED_NOTICE} and not supported:
            return "unsupported_public_communication"
        if action.action_type == ActionType.WRITE_MEMORY and not supported:
            return "unsupported_memory_write"
        if requires_escalation and not state.human_approval:
            return "missed_escalation"
        if (
            action.action_type == ActionType.REROUTE_TRAFFIC
            and state.scenario.pollution_zone_active
            and not state.emergency_priority_active
        ):
            return "pollution_zone_reroute"
        return None
