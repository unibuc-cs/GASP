"""Role ablation: rerun each scenario with one role disabled and measure the success drop.

RDC (role dependency concentration) = largest drop / sum of drops, per mode.
A value near 1 means one role carries the outcome; near 1/k means the roles
share it.  This replaces the ESEM proxy, which counted positive-reward records.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from gasp.core.env import EnvConfig, run_episode
from gasp.core.rules import RuleSet
from gasp.policies import make_policy


def role_ablation(domain, scenarios, rules: RuleSet, modes: List[Tuple[str, str, bool, str]], max_steps: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for activation, brain, guarded, label in modes:
        policy = make_policy(domain, rules, brain)
        cfg = EnvConfig(activation=activation, guarded=guarded, rule_set=rules.id, mode_name=label)
        base = {sc.scenario_id: run_episode(domain, sc, policy, cfg, rules).success for sc in scenarios}
        drops: Dict[str, float] = {}
        for role in domain.service_roles:
            affected = [sc for sc in scenarios if role in sc.required_roles]
            if not affected:
                continue
            drop = 0.0
            for sc in affected:
                res = run_episode(domain, sc, policy, cfg, rules, disabled_roles=[role])
                drop += (1.0 if base[sc.scenario_id] else 0.0) - (1.0 if res.success else 0.0)
            drops[role] = drop / len(affected)
        total = sum(max(0.0, d) for d in drops.values())
        rdc = (max(drops.values()) / total) if total > 0 else None
        out[label] = {"success_drop_by_role": drops, "rdc": rdc}
    return out
