"""Episode runner: governed execution loop with typed traces.

One step: resolve pending approvals, build every active role's observation,
collect proposals, pass each proposal through the guard, execute what is
allowed, write one trace record per proposal, check the success condition.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from .actions import ActionType, GuardOutcome, RiskLevel, TypedAction
from .domain import Scenario
from .guard import GovernanceGuard
from .rules import RuleSet
from .state import State
from .traces import TraceRecord


@dataclass
class EnvConfig:
    activation: str = "scenario"       # scenario | all | direct
    guarded: bool = True
    rule_set: str = "R2"
    mode_name: str = "unnamed"
    overseer_available: Optional[bool] = None   # override the scenario's value (sensitivity runs)
    max_steps: Optional[int] = None


class Policy(Protocol):
    name: str

    def reset(self, scenario: Scenario) -> None: ...
    def act(self, role: str, observation: Dict[str, Any], state: Optional[State] = None) -> TypedAction: ...


@dataclass
class EpisodeResult:
    scenario_id: str
    family: str
    mode: str
    success: bool
    steps: int
    active_roles: List[str]
    required_roles: List[str]
    records: List[TraceRecord]
    final_flags: Dict[str, bool]
    progress_by_role: Dict[str, float] = field(default_factory=dict)
    approvals: Dict[str, str] = field(default_factory=dict)


def activate(domain, scenario: Scenario, activation: str) -> List[str]:
    if activation == "direct":
        return ["DirectController"]
    if activation == "all":
        return list(domain.service_roles)
    if activation == "scenario":
        return list(scenario.required_roles)
    raise ValueError(activation)


class Episode:
    def __init__(self, domain, scenario: Scenario, config: EnvConfig, rule_set: Optional[RuleSet] = None):
        self.domain = domain
        self.config = config
        self.rules = rule_set or RuleSet.named(config.rule_set)
        self.scenario = copy.deepcopy(scenario)
        if config.overseer_available is not None:
            self.scenario.overseer_available = bool(config.overseer_available)
        if config.max_steps is not None:
            self.scenario.max_steps = int(config.max_steps)
        self.guard = GovernanceGuard(domain, self.rules, enabled=config.guarded)
        self.state = State(scenario=self.scenario)
        for ev in domain.build_evidence(self.scenario):
            self.state.evidence[ev.id] = ev
        self.state.active_roles = activate(domain, self.scenario, config.activation)
        self.records: List[TraceRecord] = []
        self.progress_by_role: Dict[str, float] = {}
        self.done = False

    # ------------------------------------------------------------------
    def observation(self, role: str) -> Dict[str, Any]:
        st = self.state
        sc = self.scenario
        visible_flags = {k: bool(st.flags.get(k, False)) for k in self.domain.flags_visible_to(role)}
        my_approvals = {k: a.status for k, a in st.approvals.items()
                        if a.requested_by == role or k.split("@")[0] in {t.value for t in self.domain.role_actions.get(role, [])}}
        return {
            "role": role,
            "step": st.step,
            "max_steps": sc.max_steps,
            "scenario": {
                "family": sc.family,
                "severity": sc.severity,
                "target": sc.target,
                "overseer_available": sc.overseer_available,
                **{k: v for k, v in sc.params.items()},
            },
            "evidence": [ev.public_view() for ev in st.visible_evidence(role)],
            "flags": visible_flags,
            "emergency_priority_active": st.emergency_priority_active,
            "approvals": my_approvals,
            "last_guard": st.last_guard.get(role),
            "verification_requests": [ref for ref, asker in st.verification_requests.items()
                                      if asker != role and st.lookup(ref) is not None and st.lookup(ref).visible(role)],
            "allowed_actions": [a.value for a in self.domain.role_actions.get(role, [])],
            "active_roles": list(st.active_roles),
        }

    def observations(self) -> Dict[str, Dict[str, Any]]:
        return {role: self.observation(role) for role in self.state.active_roles}

    # ------------------------------------------------------------------
    def _normalize(self, role: str, action: Optional[TypedAction]) -> tuple[TypedAction, bool]:
        """Validate a proposal. Invalid proposals become noop and are flagged."""

        allowed = set(self.domain.role_actions.get(role, []))
        if action is None or action.action_type not in allowed:
            return TypedAction(role=role, action_type=ActionType.NOOP, target=self.scenario.target,
                               rationale="invalid proposal replaced by noop"), True
        spec = self.domain.action_specs[action.action_type]
        action.role = role
        action.risk_level = spec.risk
        if not action.target:
            action.target = self.scenario.target
        payload = dict(self.domain.default_payload(self.state, action.action_type))
        payload.update(action.payload or {})
        action.payload = payload
        action.evidence_refs = [str(r) for r in (action.evidence_refs or [])]
        return action, False

    def step(self, proposals: Dict[str, Optional[TypedAction]], usage: Optional[Dict[str, Dict[str, int]]] = None) -> bool:
        """Apply one step of proposals. Returns True when the episode is over."""

        if self.done:
            return True
        st = self.state
        st.resolve_approvals()
        usage = usage or {}

        for role in list(st.active_roles):
            action, formatting_failure = self._normalize(role, proposals.get(role))
            before = st.snapshot()
            report = self.guard.assess(st, action)
            decision = self.guard.check(st, action)
            executed_action = decision.transformed_action or action
            progress = 0.0
            if decision.executed:
                progress = self.domain.apply(st, executed_action, supported=report.supported, cited_false=report.cited_false)
                self.progress_by_role[role] = self.progress_by_role.get(role, 0.0) + progress
            spec = self.domain.action_specs[action.action_type]
            executed_violation = bool(decision.executed and decision.attempted_violation and decision.outcome != GuardOutcome.SANITIZE)
            escalation = decision.outcome == GuardOutcome.ESCALATE or action.action_type == ActionType.ESCALATE
            st.last_guard[role] = {
                "action": action.action_type.value,
                "target": action.target,
                "outcome": decision.outcome.value,
                "rule_id": decision.rule_id,
                "reason": decision.reason,
                "executed": decision.executed,
            }
            tok = usage.get(role, {})
            rec = TraceRecord(
                scenario_id=self.scenario.scenario_id,
                family=self.scenario.family,
                mode=self.config.mode_name,
                step=st.step,
                role=role,
                action=action.to_dict(),
                guard=decision.to_dict(),
                executed=decision.executed,
                high_impact=spec.high_impact,
                attempted_violation=decision.attempted_violation,
                executed_violation=executed_violation,
                violation_type=decision.violation_type,
                rule_id=decision.rule_id,
                supported=report.supported,
                refs_total=report.refs_total,
                refs_invalid=report.refs_invalid,
                cited_false=report.cited_false,
                cited_unverified=report.cited_unverified,
                requires_approval=decision.requires_approval or self.domain.requires_approval(st, action, self.rules.cfg("approval")) if self.rules.enabled("approval") else False,
                approval_granted=st.is_approved(action.key),
                escalation=escalation,
                needs_approval_prob=action.needs_approval_prob,
                off_target=(action.target == getattr(self.domain, "distractor_target", None)) and action.action_type != ActionType.NOOP,
                formatting_failure=formatting_failure,
                tokens_in=int(tok.get("tokens_in", 0)),
                tokens_out=int(tok.get("tokens_out", 0)),
                state_before=before,
                state_after=st.snapshot(),
                rationale=action.rationale,
            )
            self.records.append(rec)

        st.step += 1
        st.resolve_approvals()   # answers that are due become visible in the next observations
        if self.domain.is_success(st) or st.halted or st.step >= self.scenario.max_steps:
            self.done = True
        return self.done

    def result(self) -> EpisodeResult:
        return EpisodeResult(
            scenario_id=self.scenario.scenario_id,
            family=self.scenario.family,
            mode=self.config.mode_name,
            success=self.domain.is_success(self.state),
            steps=self.state.step,
            active_roles=list(self.state.active_roles),
            required_roles=list(self.scenario.required_roles),
            records=list(self.records),
            final_flags=dict(self.state.flags),
            progress_by_role=dict(self.progress_by_role),
            approvals={k: a.status for k, a in self.state.approvals.items()},
        )


def run_episode(domain, scenario: Scenario, policy: Policy, config: EnvConfig, rule_set: Optional[RuleSet] = None,
                disabled_roles: Optional[List[str]] = None) -> EpisodeResult:
    """Run one scenario to the end with one policy object serving every role."""

    ep = Episode(domain, scenario, config, rule_set)
    if disabled_roles:
        ep.state.active_roles = [r for r in ep.state.active_roles if r not in set(disabled_roles)]
    policy.reset(ep.scenario)
    while not ep.done:
        obs = ep.observations()
        proposals: Dict[str, Optional[TypedAction]] = {}
        usage: Dict[str, Dict[str, int]] = {}
        for role, o in obs.items():
            proposals[role] = policy.act(role, o, ep.state)
            u = getattr(policy, "last_usage", None)
            if u:
                usage[role] = dict(u)
        ep.step(proposals, usage)
    return ep.result()
