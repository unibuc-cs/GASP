from gasp.core.env import EnvConfig, run_episode
from gasp.core.rules import RuleSet
from gasp.domains import get_domain
from gasp.experiments.common import make_scenarios
from gasp.policies.llm import LLMRolePolicy, MockBackend, parse_action, system_prompt
from gasp.core.actions import ActionType


def test_parse_action_accepts_valid_json_with_noise():
    text = 'Sure. {"action_type": "dispatch_ambulance", "target": "hospital_route", "evidence_refs": ["E1"], "needs_approval_prob": 0.1, "rationale": "go"} done'
    a, err = parse_action(text, "EmergencyAgent", [ActionType.DISPATCH_AMBULANCE], "hospital_route")
    assert err is None and a.action_type == ActionType.DISPATCH_AMBULANCE and a.evidence_refs == ["E1"] and a.needs_approval_prob == 0.1


def test_parse_action_skips_thinking_drafts_and_fences():
    # A local reasoning model: thinking left inline (with a JSON draft in it), then the answer in a code fence.
    text = ('<think>Maybe {"action_type": "noop"}? No, the route is blocked.</think>\n'
            '```json\n{"action_type": "reroute_traffic", "target": "r1", "evidence_refs": ["E2"], "needs_approval_prob": 0.2}\n```')
    a, err = parse_action(text, "TrafficAgent", [ActionType.REROUTE_TRAFFIC, ActionType.NOOP], "x")
    assert err is None and a.action_type == ActionType.REROUTE_TRAFFIC and a.evidence_refs == ["E2"]
    # Unterminated thinking followed by the answer; and thinking with no answer at all.
    a, err = parse_action('<think>hmm {"a": 1}\n{"action_type": "noop"}', "TrafficAgent", [ActionType.NOOP], "x")
    assert err is None and a.action_type == ActionType.NOOP
    a, err = parse_action("<think>still thinking about {braces", "TrafficAgent", [ActionType.NOOP], "x")
    assert a is None


def test_parse_action_rejects_disallowed_and_garbage():
    a, err = parse_action('{"action_type": "restore_power"}', "TrafficAgent", [ActionType.REROUTE_TRAFFIC], "x")
    assert a is None and "not allowed" in err
    a, err = parse_action("no json here", "TrafficAgent", [ActionType.REROUTE_TRAFFIC], "x")
    assert a is None


def test_llm_policy_runs_episode_with_mock_and_counts_formatting_failures():
    domain = get_domain("smartcity")
    rules = RuleSet.named("R2")
    backend = MockBackend(["garbage", "still garbage",
                           '{"action_type": "query_evidence", "payload": {"topic": "incident"}, "evidence_refs": ["GHOST"], "needs_approval_prob": 0.0}'])
    policy = LLMRolePolicy(domain, backend, rules, include_rules=True, temperature=0.7)
    sc = make_scenarios(domain, 1, 1, {"max_steps": 3})[0]
    res = run_episode(domain, sc, policy, EnvConfig(activation="scenario", guarded=True, rule_set="R2", mode_name="t"), rules)
    assert any(r.formatting_failure for r in res.records)
    assert any(r.refs_invalid > 0 for r in res.records)        # the GHOST citation is a hallucinated reference
    assert sum(r.tokens_in + r.tokens_out for r in res.records) > 0


def test_system_prompt_variants():
    domain = get_domain("smartcity")
    rules = RuleSet.named("R2")
    with_rules = system_prompt(domain, "TrafficAgent", rules, True)
    without = system_prompt(domain, "TrafficAgent", rules, False)
    assert "Operating rules" in with_rules and "Operating rules" not in without
    assert "open_bus_lane" in with_rules
