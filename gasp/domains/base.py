"""Shared domain machinery: the five common actions, discovery, verification permission, idle roles.

A concrete domain supplies roles, catalogues, scenario sampling, evidence,
effects of its own actions, success, approval kinds and sanitisation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from gasp.core.actions import ActionType, TypedAction
from gasp.core.domain import Scenario
from gasp.core.evidence import Evidence, UNVERIFIED, VERIFIED
from gasp.core.state import State


class BaseDomain:
    name = "base"
    service_roles: List[str] = []
    role_actions: Dict[str, List[ActionType]] = {}
    action_specs: Dict[ActionType, Any] = {}
    outcome_flags: List[str] = []
    required_roles_by_family: Dict[str, List[str]] = {}
    role_goals: Dict[str, Dict[str, list]] = {}
    goal_flags: Dict[str, str] = {}
    incident_owner: Dict[str, str] = {}
    primary_topic: Dict[str, str] = {}
    topic_visibility: Dict[str, List[str]] = {}
    main_target: Dict[str, str] = {}
    distractor_target: str = "elsewhere"
    society_description: str = ""
    role_jobs: Dict[str, str] = {}
    public_flag: str = "public_alert_sent"          # the flag the communication role sets

    # ---- hooks a domain implements -----------------------------------
    def families(self) -> List[str]:
        return list(self.required_roles_by_family)

    def visible_to(self, *topics: str) -> frozenset:
        roles = {"DirectController"}
        for t in topics:
            roles.update(self.topic_visibility.get(t, []))
        return frozenset(roles)

    def primary_evidence(self, sc: Scenario) -> Evidence:
        raise NotImplementedError

    def secondary_evidence(self, sc: Scenario) -> Optional[Evidence]:
        return None

    def apply_domain_action(self, state: State, action: TypedAction, supported: bool, cited_false: bool) -> float:
        raise NotImplementedError

    def sanitize(self, state: State, action: TypedAction, rules):
        return None

    def approval_kind(self, state: State, action: TypedAction, cfg: Dict[str, Any]) -> Optional[str]:
        return None

    def flags_visible_to(self, role: str) -> List[str]:
        return list(self.outcome_flags)

    def default_payload(self, state: State, action_type: ActionType) -> Dict[str, Any]:
        if action_type == ActionType.WRITE_MEMORY:
            return {"claim": "incident state updated", "expires_in": 4}
        return {}

    # ---- shared behaviour -------------------------------------------
    def requires_approval(self, state: State, action: TypedAction, cfg: Dict[str, Any]) -> bool:
        return self.approval_kind(state, action, cfg) is not None

    def discover_evidence(self, state: State, role: str, topic: str) -> List[Evidence]:
        """query_evidence: when the incident has not been reported yet, a role that works on the topic
        can find the primary report (E1) or the family's second item (E5)."""

        sc = state.scenario
        if sc.evidence_quality != "missing":
            return []
        if not (role == "DirectController" or role in self.topic_visibility.get(topic, [])):
            return []
        found: List[Evidence] = []
        if topic == self.primary_topic[sc.family] and "E1" not in state.evidence:
            e1 = self.primary_evidence(sc)
            e1.status = UNVERIFIED
            state.evidence["E1"] = e1
            found.append(e1)
        e5 = self.secondary_evidence(sc)
        if e5 is not None and e5.topic == topic and "E5" not in state.evidence:
            e5.status = UNVERIFIED
            state.evidence["E5"] = e5
            found.append(e5)
        return found

    def apply(self, state: State, action: TypedAction, supported: bool, cited_false: bool) -> float:
        at = action.action_type
        if at == ActionType.NOOP:
            return 0.0
        if at == ActionType.QUERY_EVIDENCE:
            return 0.1 if self.discover_evidence(state, action.role, str(action.payload.get("topic", ""))) else 0.0
        if at == ActionType.REQUEST_VERIFICATION:
            ref = str(action.payload.get("ref", ""))
            ev = state.lookup(ref)
            if ev is None or ev.kind == "memory_note":
                return 0.0
            if not (action.role == "DirectController" or action.role in self.topic_visibility.get(ev.topic, [])):
                # Forward the request: the item becomes visible to the roles that can check it.
                if ev.status not in (VERIFIED, "refuted") and ref not in state.verification_requests:
                    state.verification_requests[ref] = action.role
                    ev.visible_to = frozenset(set(ev.visible_to) | set(self.topic_visibility.get(ev.topic, [])))
                    return 0.05
                return 0.0
            before = ev.status
            state.verify(ref)
            return 0.1 if before != ev.status else 0.0
        if at == ActionType.ESCALATE:
            for_action = str(action.payload.get("for_action", ""))
            target = str(action.payload.get("target", action.target))
            if not for_action:
                return 0.0
            justified = any((state.lookup(r) is not None and state.lookup(r).is_verified()) for r in action.evidence_refs)
            state.request_approval(f"{for_action}@{target}", action.role, justified=justified)
            return 0.05
        if at == ActionType.WRITE_MEMORY:
            note = state.add_memory_note(
                role=action.role,
                claim=str(action.payload.get("claim", "incident state updated")),
                source_ref=str(action.payload.get("source_ref", "")),
                topic=str(action.payload.get("topic", "incident")),
                target=str(action.payload.get("target", state.scenario.target)),
                expires_in=action.payload.get("expires_in"),
            )
            return 0.1 if note.is_verified() else 0.0
        return self.apply_domain_action(state, action, supported, cited_false)

    def role_idle(self, state: State, role: str) -> bool:
        """A role with nothing left to do is not asked for an action (saves model calls, no effect on metrics)."""

        fam = state.scenario.family
        if role == "DirectController" or self.role_goals.get(fam, {}).get(role) is None:
            return False
        if not state.flags.get(self.goal_flags[role], False):
            return False
        if role == self.incident_owner[fam] and not state.flags.get(self.public_flag, False):
            note = any(n.topic == "incident" and n.is_verified() and (n.expires_at is None or n.expires_at > state.step)
                       for n in state.memory.values())
            if not note:
                return False
        for ref, asker in state.verification_requests.items():
            ev = state.evidence.get(ref)
            if ev is not None and asker != role and ev.visible(role) and role in self.topic_visibility.get(ev.topic, []):
                return False
        return True
