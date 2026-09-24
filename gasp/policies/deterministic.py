"""Deterministic role policies.

ProceduralPolicy   knows the rules and follows a compliant procedure: verify,
                   write the confirmation note, ask for approval, then act.
NaivePolicy        does not know the rules: acts as soon as it sees anything
                   on topic, cites whatever it sees, and only adapts when the
                   guard pushes back (its feedback is in the observation).
DirectControllerPolicy  one controller doing every role's job in sequence,
                   with either of the two brains above.

Both brains read only the observation dictionary the environment gives every
role, so they see exactly what an LLM role would see.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from gasp.core.actions import ActionType, TypedAction
from gasp.core.domain import Scenario
from gasp.core.rules import RuleSet
from gasp.core.state import State


GOAL_FLAG = {
    "TrafficAgent": "route_secured",
    "EmergencyAgent": "ambulance_dispatched",
    "EnergyAgent": "power_restored",
    "WaterAgent": "water_hazard_closed",
    "PollutionAgent": "pollution_mitigated",
    "PublicTransportAgent": "transport_capacity_added",
    "PublicWorksAgent": "repair_crew_dispatched",
    "CitizenCommsAgent": "public_alert_sent",
}


def _evidence(obs: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(obs.get("evidence", []))


def _on_topics(obs: Dict[str, Any], topics: Tuple[str, ...], statuses: Tuple[str, ...]) -> List[Dict[str, Any]]:
    return [e for e in _evidence(obs) if e["topic"] in topics and e["status"] in statuses]


class _Brain:
    """Shared machinery for the two deterministic brains."""

    name = "brain"

    def __init__(self, domain, rules: RuleSet, rules_known: bool):
        self.domain = domain
        self.rules = rules
        self.rules_known = rules_known
        self.last_usage = None

    def reset(self, scenario: Scenario) -> None:
        self.notes_written: Dict[str, bool] = {}
        self.queried: Dict[str, bool] = {}

    # -- helpers ---------------------------------------------------------
    def can_verify(self, role: str, topic: str) -> bool:
        if role == "DirectController":
            return True
        return role in self.domain_topic_visibility().get(topic, [])

    def domain_topic_visibility(self) -> Dict[str, List[str]]:
        from gasp.domains.smartcity import TOPIC_VISIBILITY
        return TOPIC_VISIBILITY

    def spec(self, action_type: ActionType):
        return self.domain.action_specs[action_type]

    def requires_approval_obs(self, obs: Dict[str, Any], action: TypedAction) -> bool:
        """Approval requirement as the policy can compute it from its observation (rules known only)."""

        if not (self.rules_known and self.rules.enabled("approval")):
            return False
        cfg = self.rules.cfg("approval")
        sc = obs["scenario"]
        at = action.action_type
        spec = self.spec(at)
        if cfg.get("all_high_risk") and spec.risk.value == "high":
            return True
        thr = cfg.get("bus_lane_duration_threshold")
        if at == ActionType.OPEN_BUS_LANE and thr is not None and float(action.payload.get("duration", 8)) > float(thr):
            return True
        if at == ActionType.CLOSE_ROAD and cfg.get("close_road_hospital_risk") and sc.get("hospital_access_risk"):
            return True
        if at == ActionType.ISOLATE_GRID_SEGMENT and cfg.get("isolate_grid_when_power_bad") and sc.get("power_bad"):
            return True
        bthr = cfg.get("broadcast_severity_threshold")
        if at == ActionType.BROADCAST_ALERT and bthr is not None and int(sc.get("severity", 1)) >= int(bthr):
            return True
        return False

    def goals_for(self, role: str, family: str, virtual_role: Optional[str] = None):
        vrole = virtual_role or role
        return self.domain.role_goals.get(family, {}).get(vrole)

    def note_exists(self, obs: Dict[str, Any]) -> bool:
        return any(e["kind"] == "memory_note" and e["topic"] == "incident" and e["status"] == "verified" for e in _evidence(obs))

    def serve_requests(self, role: str, obs: Dict[str, Any]) -> Optional[TypedAction]:
        """Another role asked for a check on evidence this role can verify."""

        for ref in obs.get("verification_requests", []):
            ev = next((e for e in _evidence(obs) if e["id"] == ref), None)
            if ev is not None and ev["status"] in ("unverified", "conflicting") and self.can_verify(role, ev["topic"]):
                return self.make(role, ActionType.REQUEST_VERIFICATION, obs["scenario"]["target"], [ref], {"ref": ref}, 0.0,
                                 "another role asked for this report to be checked")
        return None

    def forward_request(self, role: str, obs: Dict[str, Any], candidates: List[Dict[str, Any]], why: str) -> Optional[TypedAction]:
        """Ask for verification of evidence this role cannot check itself (once per item)."""

        for e in candidates:
            if e["kind"] == "memory_note" or self.queried.get(f"fwd:{e['id']}"):
                continue
            self.queried[f"fwd:{e['id']}"] = True
            return self.make(role, ActionType.REQUEST_VERIFICATION, obs["scenario"]["target"], [e["id"]], {"ref": e["id"]}, 0.0, why)
        return None

    def make(self, role: str, at: ActionType, target: str, refs: List[str], payload: Optional[Dict[str, Any]] = None,
             p_approval: Optional[float] = None, why: str = "") -> TypedAction:
        return TypedAction(role=role, action_type=at, target=target, payload=payload or {}, evidence_refs=list(refs),
                           needs_approval_prob=p_approval, rationale=why)


class ProceduralPolicy(_Brain):
    """Compliant procedure. Serves as the deterministic reference and as the reachability check."""

    name = "procedural"

    def __init__(self, domain, rules: RuleSet):
        super().__init__(domain, rules, rules_known=True)

    def act(self, role: str, obs: Dict[str, Any], state: Optional[State] = None, virtual_role: Optional[str] = None) -> TypedAction:
        fam = obs["scenario"]["family"]
        target = obs["scenario"]["target"]
        vrole = virtual_role or role
        goals = self.goals_for(role, fam, vrole)
        noop = self.make(role, ActionType.NOOP, target, [], why="nothing to do")
        if not goals:
            return noop
        primary, fallback = goals[0]
        owner = self.domain.incident_owner[fam]
        primary_topic = self.domain.primary_topic[fam]
        achieved = bool(obs["flags"].get(GOAL_FLAG.get(vrole, ""), False))

        # Owner writes the confirmation note once its own action is done (or first, if the note is all that is missing).
        if vrole == owner and achieved and not self.note_exists(obs) and self.rules_known:
            verified_primary = _on_topics(obs, (primary_topic,), ("verified",))
            if verified_primary:
                src = verified_primary[0]["id"]
                return self.make(role, ActionType.WRITE_MEMORY, target, [src],
                                 {"claim": f"{fam.replace('_', ' ')} at {target} confirmed", "source_ref": src,
                                  "expires_in": 8, "topic": "incident", "target": target}, 0.0,
                                 "shared confirmation note for the other roles")
            unv = [e for e in _on_topics(obs, (primary_topic,), ("unverified", "conflicting")) if self.can_verify(role, e["topic"])]
            if unv:
                return self.make(role, ActionType.REQUEST_VERIFICATION, target, [unv[0]["id"]], {"ref": unv[0]["id"]}, 0.0,
                                 "verify before writing the note")
            if not _on_topics(obs, (primary_topic,), ("verified", "unverified", "conflicting")) \
                    and self.can_verify(role, primary_topic) and not self.queried.get(f"{role}:{primary_topic}"):
                self.queried[f"{role}:{primary_topic}"] = True
                return self.make(role, ActionType.QUERY_EVIDENCE, target, [], {"topic": primary_topic}, 0.0,
                                 "find the report so the note can cite it")
        if achieved:
            return self.serve_requests(role, obs) or noop

        action_type = primary
        approvals = obs.get("approvals", {})
        key_primary = f"{primary.value}@{target}"
        last = obs.get("last_guard") or {}
        if approvals.get(key_primary) == "denied" or (last.get("action") == primary.value and last.get("outcome") == "deny"):
            if fallback is None:
                return noop
            action_type = fallback
        # Known pollution-zone rule: avoid the reroute the guard would rewrite anyway.
        if (action_type == ActionType.REROUTE_TRAFFIC and self.rules.enabled("pollution_zone")
                and obs["scenario"].get("pollution_zone_active") and not obs.get("emergency_priority_active")):
            action_type = ActionType.CHANGE_SIGNAL_PRIORITY

        spec = self.spec(action_type)
        needs_evidence = bool(spec.evidence_topics) and (
            (spec.public and self.rules.enabled("public_comm"))
            or (self.rules.enabled("evidence") and spec.risk.value in self.rules.cfg("evidence").get("risk_levels", []))
        )
        refs: List[str] = []
        if spec.evidence_topics:
            verified = _on_topics(obs, spec.evidence_topics, ("verified",))
            refs = [verified[0]["id"]] if verified else []
            if not refs and needs_evidence:
                unv = [e for e in _on_topics(obs, spec.evidence_topics, ("unverified", "conflicting"))
                       if self.can_verify(role, e["topic"]) and e["kind"] != "memory_note"]
                if unv:
                    return self.make(role, ActionType.REQUEST_VERIFICATION, target, [unv[0]["id"]], {"ref": unv[0]["id"]}, 0.0,
                                     "verify the evidence before acting")
                for topic in spec.evidence_topics:
                    if self.can_verify(role, topic) and not _on_topics(obs, (topic,), ("verified", "unverified", "conflicting")) \
                            and not self.queried.get(f"{role}:{topic}"):
                        self.queried[f"{role}:{topic}"] = True
                        return self.make(role, ActionType.QUERY_EVIDENCE, target, [], {"topic": topic}, 0.0, "look for the missing report")
                fwd = self.forward_request(role, obs, _on_topics(obs, spec.evidence_topics, ("unverified", "conflicting")),
                                           "cannot check this myself; asking for verification")
                if fwd is not None:
                    return fwd
                return self.make(role, ActionType.NOOP, target, [], why="waiting for verified evidence or a confirmation note")

        action = self.make(role, action_type, target, refs, dict(self.domain.default_payload(state, action_type)) if state else {}, 0.0, "planned action")
        if self.requires_approval_obs(obs, action):
            action.needs_approval_prob = 1.0
            status = approvals.get(action.key)
            if status == "approved":
                return action
            if status == "pending":
                return self.make(role, ActionType.NOOP, target, [], why="waiting for approval")
            if status == "denied":
                if fallback is not None and action_type != fallback:
                    alt = self.make(role, fallback, target, refs, {}, 0.0, "approval denied, using the fallback")
                    if self.requires_approval_obs(obs, alt):
                        return self.make(role, ActionType.NOOP, target, [], why="fallback also needs approval; giving up")
                    return alt
                return noop
            return self.make(role, ActionType.ESCALATE, target, refs, {"for_action": action_type.value, "target": target}, 1.0,
                             "this action needs approval; asking the overseer")
        return action


class NaivePolicy(_Brain):
    """Does not know the rules. Acts immediately, cites everything on topic, adapts only to guard feedback."""

    name = "naive"

    def __init__(self, domain, rules: RuleSet):
        super().__init__(domain, rules, rules_known=False)

    def reset(self, scenario: Scenario) -> None:
        super().reset(scenario)
        self.note_denied: Dict[str, bool] = {}

    def act(self, role: str, obs: Dict[str, Any], state: Optional[State] = None, virtual_role: Optional[str] = None) -> TypedAction:
        fam = obs["scenario"]["family"]
        target = obs["scenario"]["target"]
        vrole = virtual_role or role
        goals = self.goals_for(role, fam, vrole)
        noop = self.make(role, ActionType.NOOP, target, [], p_approval=0.0, why="nothing to do")
        last = obs.get("last_guard") or {}
        approvals = obs.get("approvals", {})
        if not goals:
            return self._eager(role, obs, last)
        primary, fallback = goals[0]
        owner = self.domain.incident_owner[fam]
        primary_topic = self.domain.primary_topic[fam]
        achieved = bool(obs["flags"].get(GOAL_FLAG.get(vrole, ""), False))

        # Sloppy note: the owner shares what it did, citing whatever it has, without expiry.  If the
        # guard rejects the note, it learns from the reason and retries with a verified source and an expiry.
        if vrole == owner and achieved and not self.notes_written.get(role) and not self.note_exists(obs):
            if last.get("action") == "write_memory" and last.get("outcome") == "deny":
                self.note_denied[role] = True
            any_primary = _on_topics(obs, (primary_topic,), ("verified", "unverified", "conflicting"))
            verified_primary = [e for e in any_primary if e["status"] == "verified"]
            if self.note_denied.get(role):
                if verified_primary:
                    self.notes_written[role] = True
                    src = verified_primary[0]["id"]
                    return self.make(role, ActionType.WRITE_MEMORY, target, [src],
                                     {"claim": f"{fam.replace('_', ' ')} at {target}", "source_ref": src, "expires_in": 8,
                                      "topic": "incident", "target": target}, 0.0, "note rejected once; retrying with source and expiry")
                unv = [e for e in any_primary if e["status"] != "verified" and self.can_verify(role, e["topic"])]
                if unv:
                    return self.make(role, ActionType.REQUEST_VERIFICATION, target, [unv[0]["id"]], {"ref": unv[0]["id"]}, 0.0,
                                     "note rejected; verifying the source first")
                if not any_primary and self.can_verify(role, primary_topic) and not self.queried.get(f"{role}:{primary_topic}"):
                    self.queried[f"{role}:{primary_topic}"] = True
                    return self.make(role, ActionType.QUERY_EVIDENCE, target, [], {"topic": primary_topic}, 0.0, "note rejected; looking for a source")
                return noop
            if any_primary:
                src = any_primary[0]["id"]
                if last.get("action") == "write_memory" and last.get("outcome") == "allow":
                    self.notes_written[role] = True
                    return noop
                return self.make(role, ActionType.WRITE_MEMORY, target, [src],
                                 {"claim": f"{fam.replace('_', ' ')} at {target}", "source_ref": src, "expires_in": None,
                                  "topic": "incident", "target": target}, 0.0, "sharing what I did")
            if self.can_verify(role, primary_topic) and not self.queried.get(f"{role}:{primary_topic}"):
                self.queried[f"{role}:{primary_topic}"] = True
                return self.make(role, ActionType.QUERY_EVIDENCE, target, [], {"topic": primary_topic}, 0.0, "looking for something to share")
            return noop
        if achieved:
            return self.serve_requests(role, obs) or noop

        action_type = primary
        if approvals.get(f"{primary.value}@{target}") == "denied" or (last.get("action") == primary.value and last.get("outcome") == "deny"):
            if fallback is None:
                return noop
            action_type = fallback
        spec = self.spec(action_type)
        on_topic = _on_topics(obs, spec.evidence_topics, ("verified", "unverified", "conflicting")) if spec.evidence_topics else []
        verified = [e for e in on_topic if e["status"] == "verified"]
        refs = [e["id"] for e in (verified if verified else on_topic)]
        key = f"{action_type.value}@{target}"

        # React to what the guard said about the last attempt.
        if last.get("action") == action_type.value:
            if last.get("outcome") == "request_evidence":
                unv = [e for e in on_topic if e["status"] != "verified" and self.can_verify(role, e["topic"]) and e["kind"] != "memory_note"]
                if unv:
                    return self.make(role, ActionType.REQUEST_VERIFICATION, target, [unv[0]["id"]], {"ref": unv[0]["id"]}, 0.0,
                                     "the guard asked for evidence; verifying what I can")
                if not verified:
                    for topic in spec.evidence_topics:
                        if not on_topic and self.can_verify(role, topic) and not self.queried.get(f"{role}:{topic}"):
                            self.queried[f"{role}:{topic}"] = True
                            return self.make(role, ActionType.QUERY_EVIDENCE, target, [], {"topic": topic}, 0.0, "looking for evidence")
                    fwd = self.forward_request(role, obs, [e for e in on_topic if e["status"] != "verified"],
                                               "the guard wants verified evidence; asking someone who can check")
                    if fwd is not None:
                        return fwd
                    return self.make(role, ActionType.NOOP, target, [], p_approval=0.0, why="blocked for lack of evidence; waiting")
            if last.get("outcome") == "escalate":
                status = approvals.get(key)
                if status == "approved":
                    return self.make(role, action_type, target, refs, {}, 0.0, "approved; acting")
                if status == "denied":
                    if fallback is not None and fallback != action_type:
                        return self.make(role, fallback, target, refs, {}, 0.0, "approval denied; fallback")
                    return noop
                return self.make(role, ActionType.NOOP, target, [], p_approval=0.0, why="waiting for the overseer")
        elif approvals.get(key) == "approved":
            return self.make(role, action_type, target, refs, {}, 0.0, "approved; acting")

        if spec.evidence_topics and not on_topic:
            for topic in spec.evidence_topics:
                if self.can_verify(role, topic) and not self.queried.get(f"{role}:{topic}"):
                    self.queried[f"{role}:{topic}"] = True
                    return self.make(role, ActionType.QUERY_EVIDENCE, target, [], {"topic": topic}, 0.0, "looking for evidence")
        return self.make(role, action_type, target, refs, {}, 0.0, "acting on what I see")

    def _eager(self, role: str, obs: Dict[str, Any], last: Dict[str, Any]) -> TypedAction:
        """A role that is active but has no job in this incident still acts on what it sees, once."""

        target = obs["scenario"]["target"]
        if self.notes_written.get(f"eager:{role}") or last.get("outcome") == "deny":
            return self.make(role, ActionType.NOOP, target, [], p_approval=0.0, why="nothing to do")
        specific = [a for a in self.domain.role_actions.get(role, []) if a not in {ActionType.NOOP, ActionType.QUERY_EVIDENCE,
                    ActionType.REQUEST_VERIFICATION, ActionType.ESCALATE, ActionType.WRITE_MEMORY}]
        for at in specific:
            spec = self.spec(at)
            seen = [e for e in _evidence(obs) if e["kind"] != "memory_note" and (not spec.evidence_topics or e["topic"] in spec.evidence_topics)]
            if seen:
                self.notes_written[f"eager:{role}"] = True
                return self.make(role, at, seen[0]["target"], [seen[0]["id"]], {}, 0.0, "not my incident, but I see something I can act on")
        return self.make(role, ActionType.NOOP, target, [], p_approval=0.0, why="nothing to do")


class DirectControllerPolicy:
    """One controller does every role's job in sequence (activation 'direct')."""

    name = "direct"

    def __init__(self, domain, rules: RuleSet, brain: str = "procedural"):
        self.domain = domain
        self.brain = ProceduralPolicy(domain, rules) if brain == "procedural" else NaivePolicy(domain, rules)
        self.name = f"direct_{self.brain.name}"
        self.last_usage = None

    def reset(self, scenario: Scenario) -> None:
        self.brain.reset(scenario)

    def act(self, role: str, obs: Dict[str, Any], state: Optional[State] = None) -> TypedAction:
        fam = obs["scenario"]["family"]
        order = list(self.domain.role_goals[fam].keys())
        owner = self.domain.incident_owner[fam]
        order.sort(key=lambda r: (0 if r == owner else (2 if r == "CitizenCommsAgent" else 1)))
        for vrole in order:
            flags = dict(obs["flags"])
            if flags.get(GOAL_FLAG[vrole], False):
                if vrole == owner and not self.brain.note_exists(obs) and self.brain.rules_known:
                    a = self.brain.act(role, obs, state, virtual_role=vrole)
                    if a.action_type != ActionType.NOOP:
                        return a
                continue
            a = self.brain.act(role, obs, state, virtual_role=vrole)
            if a.action_type != ActionType.NOOP:
                return a
        return TypedAction(role=role, action_type=ActionType.NOOP, target=obs["scenario"]["target"], needs_approval_prob=0.0,
                           rationale="all goals done or waiting")


def make_policy(domain, rules: RuleSet, name: str):
    if name == "procedural":
        return ProceduralPolicy(domain, rules)
    if name == "naive":
        return NaivePolicy(domain, rules)
    if name == "direct_procedural":
        return DirectControllerPolicy(domain, rules, "procedural")
    if name == "direct_naive":
        return DirectControllerPolicy(domain, rules, "naive")
    raise ValueError(name)
