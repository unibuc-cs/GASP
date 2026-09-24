"""One test per rule and outcome, plus the invariants the paper relies on."""

from __future__ import annotations

import random

import pytest

from gasp.core.actions import ActionType, GuardOutcome, TypedAction
from gasp.core.env import Episode, EnvConfig, run_episode
from gasp.core.guard import GovernanceGuard
from gasp.core.rules import RuleSet
from gasp.core.state import State
from gasp.domains import get_domain
from gasp.experiments.common import make_scenarios
from gasp.policies import make_policy


@pytest.fixture
def domain():
    return get_domain("smartcity")


@pytest.fixture
def rules():
    return RuleSet.named("R2")


def make_state(domain, family="traffic_accident", quality="partial", **overrides):
    rng = random.Random(1)
    sc = domain.sample_scenario(rng, family, 1, {})
    sc.evidence_quality = quality
    for k, v in overrides.items():
        if k in sc.params:
            sc.params[k] = v
        else:
            setattr(sc, k, v)
    st = State(scenario=sc)
    for ev in domain.build_evidence(sc):
        st.evidence[ev.id] = ev
    st.active_roles = list(sc.required_roles)
    return st


def act(role, at, target="hospital_route", refs=(), payload=None):
    return TypedAction(role=role, action_type=at, target=target, evidence_refs=list(refs), payload=payload or {})


# --- scope -----------------------------------------------------------------

def test_scope_denies_role_outside_required_set(domain, rules):
    st = make_state(domain)
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("WaterAgent", ActionType.DISPATCH_REPAIR_CREW))
    assert d.outcome == GuardOutcome.DENY and d.rule_id == "scope" and not d.executed


def test_scope_allows_required_role(domain, rules):
    st = make_state(domain, quality="complete")
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("EmergencyAgent", ActionType.DISPATCH_AMBULANCE, refs=["E1"]))
    assert d.outcome == GuardOutcome.ALLOW and d.executed


# --- evidence ---------------------------------------------------------------

def test_evidence_rule_blocks_high_risk_action_without_verified_citation(domain, rules):
    st = make_state(domain, quality="partial")   # E1 unverified
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("TrafficAgent", ActionType.OPEN_BUS_LANE, refs=["E1"], payload={"duration": 3}))
    assert d.outcome == GuardOutcome.REQUEST_EVIDENCE and d.rule_id == "evidence" and d.violation_type == "unsupported_action"


def test_evidence_rule_passes_with_verified_citation(domain, rules):
    st = make_state(domain, quality="complete")
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("TrafficAgent", ActionType.OPEN_BUS_LANE, refs=["E1"], payload={"duration": 3}))
    assert d.outcome == GuardOutcome.ALLOW


def test_evidence_rule_ignores_medium_risk_under_R2_but_not_R3(domain):
    st = make_state(domain, quality="partial")
    d2 = GovernanceGuard(domain, RuleSet.named("R2"), True).check(st, act("EmergencyAgent", ActionType.DISPATCH_AMBULANCE, refs=["E1"]))
    d3 = GovernanceGuard(domain, RuleSet.named("R3"), True).check(st, act("EmergencyAgent", ActionType.DISPATCH_AMBULANCE, refs=["E1"]))
    assert d2.outcome == GuardOutcome.ALLOW
    assert d3.outcome == GuardOutcome.REQUEST_EVIDENCE


def test_citing_refuted_evidence_is_unsupported(domain, rules):
    st = make_state(domain, quality="complete", false_report=True)
    st.verify("F1")
    assert st.evidence["F1"].status == "refuted"
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("TrafficAgent", ActionType.OPEN_BUS_LANE, refs=["E1", "F1"], payload={"duration": 3}))
    assert d.outcome == GuardOutcome.REQUEST_EVIDENCE


# --- public communication ---------------------------------------------------

def test_public_comm_blocks_unverified_public_report(domain, rules):
    st = make_state(domain, quality="complete")
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("CitizenCommsAgent", ActionType.SEND_TARGETED_NOTICE, refs=["E4"]))
    assert d.outcome == GuardOutcome.REQUEST_EVIDENCE and d.rule_id == "public_comm"


def test_public_comm_accepts_verified_memory_note(domain, rules):
    st = make_state(domain, quality="complete")
    note = st.add_memory_note("EmergencyAgent", "accident confirmed", "E1", "incident", "hospital_route", 8)
    assert note.is_verified()
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("CitizenCommsAgent", ActionType.SEND_TARGETED_NOTICE, refs=[note.id]))
    assert d.outcome == GuardOutcome.ALLOW


def test_public_comm_rejects_mix_of_verified_and_unverified_claims(domain, rules):
    st = make_state(domain, quality="complete", false_report=True)
    note = st.add_memory_note("EmergencyAgent", "accident confirmed", "E1", "incident", "hospital_route", 8)
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("CitizenCommsAgent", ActionType.SEND_TARGETED_NOTICE, refs=[note.id, "F1"]))
    assert d.outcome == GuardOutcome.REQUEST_EVIDENCE


# --- memory provenance ------------------------------------------------------

def test_memory_rule_denies_note_without_expiry(domain, rules):
    st = make_state(domain, quality="complete")
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("EmergencyAgent", ActionType.WRITE_MEMORY, refs=["E1"], payload={"source_ref": "E1", "expires_in": None}))
    assert d.outcome == GuardOutcome.DENY and d.rule_id == "memory_provenance"


def test_memory_rule_denies_unverified_source(domain, rules):
    st = make_state(domain, quality="partial")
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("EmergencyAgent", ActionType.WRITE_MEMORY, refs=["E1"], payload={"source_ref": "E1", "expires_in": 4}))
    assert d.outcome == GuardOutcome.DENY


def test_memory_rule_allows_verified_source_with_expiry(domain, rules):
    st = make_state(domain, quality="complete")
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("EmergencyAgent", ActionType.WRITE_MEMORY, refs=["E1"], payload={"source_ref": "E1", "expires_in": 4}))
    assert d.outcome == GuardOutcome.ALLOW


# --- approval ---------------------------------------------------------------

def test_approval_escalates_then_allows_after_latency(domain, rules):
    st = make_state(domain, quality="complete", overseer_available=True, overseer_latency=1)
    g = GovernanceGuard(domain, rules, enabled=True)
    a = act("TrafficAgent", ActionType.OPEN_BUS_LANE, refs=["E1"], payload={"duration": 8})
    d = g.check(st, a)
    assert d.outcome == GuardOutcome.ESCALATE and d.rule_id == "approval"
    assert st.approval_status(a.key) == "pending"
    st.step += 1
    st.resolve_approvals()
    assert st.approval_status(a.key) == "approved"
    assert g.check(st, a).outcome == GuardOutcome.ALLOW


def test_approval_denied_when_overseer_unavailable(domain, rules):
    st = make_state(domain, quality="complete", overseer_available=False, overseer_latency=1)
    g = GovernanceGuard(domain, rules, enabled=True)
    a = act("TrafficAgent", ActionType.OPEN_BUS_LANE, refs=["E1"], payload={"duration": 8})
    g.check(st, a)
    st.step += 1
    st.resolve_approvals()
    d = g.check(st, a)
    assert d.outcome == GuardOutcome.DENY and d.rule_id == "approval"


def test_unjustified_request_is_denied_even_with_overseer(domain, rules):
    st = make_state(domain, quality="partial", overseer_available=True, overseer_latency=1)
    g = GovernanceGuard(domain, RuleSet.named("R1"), enabled=True)   # R1 has no evidence rule, so approval is reached
    a = act("TrafficAgent", ActionType.CLOSE_ROAD, refs=["E1"])
    d = g.check(st, a)
    assert d.outcome == GuardOutcome.ESCALATE
    st.step += 1
    st.resolve_approvals()
    assert st.approval_status(a.key) == "denied"


# --- sanitize ---------------------------------------------------------------

def test_pollution_zone_reroute_is_sanitized(domain, rules):
    st = make_state(domain, family="pollution_spike", quality="complete")
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("TrafficAgent", ActionType.REROUTE_TRAFFIC, target="school_zone", refs=["E3"]))
    assert d.outcome == GuardOutcome.SANITIZE and d.executed
    assert d.transformed_action.action_type == ActionType.CHANGE_SIGNAL_PRIORITY


def test_pollution_zone_reroute_allowed_with_emergency_priority(domain, rules):
    st = make_state(domain, family="pollution_spike", quality="complete")
    st.emergency_priority_active = True
    g = GovernanceGuard(domain, rules, enabled=True)
    d = g.check(st, act("TrafficAgent", ActionType.REROUTE_TRAFFIC, target="school_zone", refs=["E3"]))
    assert d.outcome == GuardOutcome.ALLOW


# --- unguarded labelling ----------------------------------------------------

def test_unguarded_mode_executes_but_labels_the_violation(domain, rules):
    st = make_state(domain, quality="partial")
    g = GovernanceGuard(domain, rules, enabled=False)
    d = g.check(st, act("CitizenCommsAgent", ActionType.BROADCAST_ALERT, refs=["E4"]))
    assert d.outcome == GuardOutcome.ALLOW and d.executed
    assert d.attempted_violation and d.violation_type == "unsupported_public_communication"


# --- invariants over whole runs ---------------------------------------------

@pytest.mark.parametrize("policy_name", ["naive", "procedural"])
@pytest.mark.parametrize("rule_set", ["R1", "R2", "R3"])
def test_guarded_runs_have_no_executed_violations_and_no_false_alerts(domain, policy_name, rule_set):
    rules = RuleSet.named(rule_set)
    scenarios = make_scenarios(domain, 5, 11, {})
    policy = make_policy(domain, rules, policy_name)
    cfg = EnvConfig(activation="scenario", guarded=True, rule_set=rule_set, mode_name="t")
    for sc in scenarios:
        res = run_episode(domain, sc, policy, cfg, rules)
        assert not any(r.executed_violation for r in res.records)
        assert not res.final_flags.get("false_alert_sent")


def test_procedural_policy_never_attempts_a_violation(domain, rules):
    scenarios = make_scenarios(domain, 5, 3, {})
    policy = make_policy(domain, rules, "procedural")
    cfg = EnvConfig(activation="scenario", guarded=False, rule_set="R2", mode_name="t")
    for sc in scenarios:
        res = run_episode(domain, sc, policy, cfg, rules)
        assert not any(r.attempted_violation for r in res.records), sc.scenario_id


def test_scenario_set_is_stratified_and_reproducible(domain):
    a = make_scenarios(domain, 7, 99, {})
    b = make_scenarios(domain, 7, 99, {})
    assert [s.to_dict() for s in a] == [s.to_dict() for s in b]
    from collections import Counter
    assert Counter(s.family for s in a) == {f: 7 for f in domain.families()}


def test_every_scenario_is_solvable_without_violations(domain, rules):
    scenarios = make_scenarios(domain, 10, 5, {})
    policy = make_policy(domain, rules, "procedural")
    cfg = EnvConfig(activation="scenario", guarded=True, rule_set="R2", mode_name="t")
    for sc in scenarios:
        res = run_episode(domain, sc, policy, cfg, rules)
        assert res.success, sc.scenario_id


# --- hidden context and the adaptive governor ------------------------------

def test_hidden_context_denies_soft_but_not_hard_approvals(domain, rules):
    st = make_state(domain, quality="complete", overseer_available=True, overseer_latency=1, hidden_denial=True)
    g = GovernanceGuard(domain, rules, enabled=True)
    soft = act("TrafficAgent", ActionType.OPEN_BUS_LANE, refs=["E1"], payload={"duration": 8})
    hard = act("TrafficAgent", ActionType.CLOSE_ROAD, refs=["E1"])
    g.check(st, soft)
    g.check(st, hard)
    st.step += 1
    st.resolve_approvals()
    assert st.approval_status(soft.key) == "denied"
    assert st.approval_status(hard.key) == "approved"


def test_adaptive_governor_waives_soft_approval_for_trusted_role_only(domain, rules):
    st = make_state(domain, quality="complete")
    g = GovernanceGuard(domain, rules, enabled=True, adaptive_threshold=0.7)
    soft = act("TrafficAgent", ActionType.OPEN_BUS_LANE, refs=["E1"], payload={"duration": 8})
    st.trust["TrafficAgent"] = 0.5
    assert g.check(st, soft).outcome == GuardOutcome.ESCALATE
    st2 = make_state(domain, quality="complete")
    st2.trust["TrafficAgent"] = 0.9
    d = g.check(st2, soft)
    assert d.outcome == GuardOutcome.ALLOW and d.approval_waived
    hard = act("TrafficAgent", ActionType.CLOSE_ROAD, refs=["E1"])
    assert g.check(st2, hard).outcome == GuardOutcome.ESCALATE   # hard approvals are never waived


def test_hidden_harm_only_without_human_approval(domain, rules):
    scenarios = [s for s in make_scenarios(domain, 40, 5, {"hidden_denial_rate": 1.0}) if s.family == "traffic_accident"]
    # static guard: soft approvals denied, no harm; adaptive with threshold 0: waived, harm whenever the bus lane opens
    for th, expect_harm in ((None, False), (0.0, True)):
        policy = make_policy(domain, rules, "procedural")
        cfg = EnvConfig(activation="scenario", guarded=True, rule_set="R2", mode_name="t", adaptive_threshold=th)
        harms = [run_episode(domain, sc, policy, cfg, rules).final_flags.get("hidden_harm", False) for sc in scenarios]
        assert any(harms) == expect_harm
