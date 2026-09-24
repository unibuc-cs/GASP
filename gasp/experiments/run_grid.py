"""LLM experiment grid: models x modes x scenarios x repeats. Resumable.

    python -m gasp.experiments.run_grid --config configs/llm_grid.yaml --out outputs/llm \
        --scenarios outputs/paper/scenarios.json [--limit 8] [--modes M2,M3]

Every finished episode is one trace file and one line in episodes.jsonl, so a
crashed or interrupted run continues where it stopped.  Costs (tokens) are in
the traces and in the per-episode rows.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml

from gasp.core.env import EnvConfig, run_episode
from gasp.core.metrics import AGG_COLUMNS, aggregate, episode_metrics, markdown_table, write_csv
from gasp.core.rules import RuleSet
from gasp.core.traces import write_jsonl
from gasp.domains import get_domain
from gasp.experiments.common import load_scenarios, manifest
from gasp.policies.llm import LLMRolePolicy, make_backend


# activation, guarded, include_rules
MODES: Dict[str, Dict[str, Any]] = {
    "M0": {"activation": "direct", "guarded": False, "include_rules": True, "desc": "one agent, all tools, rules in prompt"},
    "M0g": {"activation": "direct", "guarded": True, "include_rules": True, "desc": "one agent, rules in prompt, guard"},
    "M1": {"activation": "scenario", "guarded": False, "include_rules": False, "desc": "roles, no rules anywhere"},
    "M2": {"activation": "scenario", "guarded": False, "include_rules": True, "desc": "roles, rules in prompts only"},
    "M3": {"activation": "scenario", "guarded": True, "include_rules": False, "desc": "roles, guard, rules not in prompts"},
    "M4": {"activation": "scenario", "guarded": True, "include_rules": True, "desc": "roles, rules in prompts and guard"},
}

TABLE_COLUMNS = ["success", "steps", "proposals", "attempted_violations", "executed_violations", "missed_approvals",
                 "overseer_load", "tsc", "hallucinated_refs", "false_alert", "silent_violation_rate", "brier",
                 "formatting_failures", "tokens", "gau"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--scenarios", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=None, help="use only the first N scenarios per family (pilot)")
    ap.add_argument("--modes", type=str, default=None, help="comma-separated subset of modes")
    ap.add_argument("--models", type=str, default=None, help="comma-separated subset of model names")
    ap.add_argument("--repeats", type=int, default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    domain = get_domain(cfg.get("domain", "smartcity"))
    rule_set_name = cfg.get("rule_set", "R2")
    rules = RuleSet.named(rule_set_name)
    repeats = args.repeats or int(cfg.get("repeats", 5))
    temperature = float(cfg.get("temperature", 0.7))
    max_steps = int(cfg.get("max_steps", 16))
    modes = [m.strip() for m in (args.modes.split(",") if args.modes else cfg.get("modes", list(MODES)))]
    models = cfg["models"]
    if args.models:
        wanted = {m.strip() for m in args.models.split(",")}
        models = [m for m in models if m["name"] in wanted]

    scenarios = load_scenarios(args.scenarios)
    if args.limit:
        per_fam: Dict[str, int] = {}
        kept = []
        for sc in scenarios:
            if per_fam.get(sc.family, 0) < args.limit:
                kept.append(sc)
                per_fam[sc.family] = per_fam.get(sc.family, 0) + 1
        scenarios = kept

    out = args.out
    trace_dir = out / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out / "episodes.jsonl"
    done = set()
    if rows_path.exists():
        for line in rows_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r["model"], r["mode"], r["scenario_id"], r["repeat"]))

    started = time.time()
    with rows_path.open("a", encoding="utf-8") as rows_f:
        for model_spec in models:
            backend = make_backend(model_spec)
            for mode in modes:
                m = MODES[mode]
                policy = LLMRolePolicy(domain, backend, rules, include_rules=m["include_rules"], temperature=temperature,
                                       cache_dir=(out / "cache") if temperature == 0 else None)
                env_cfg = EnvConfig(activation=m["activation"], guarded=m["guarded"], rule_set=rule_set_name,
                                    mode_name=mode, max_steps=max_steps)
                for sc in scenarios:
                    for rep in range(repeats):
                        key = (model_spec["name"], mode, sc.scenario_id, rep)
                        if key in done:
                            continue
                        res = run_episode(domain, sc, policy, env_cfg, rules)
                        write_jsonl(res.records, trace_dir / f"{model_spec['name']}__{mode}__{sc.scenario_id}__r{rep}.jsonl")
                        row = episode_metrics(res, max_steps)
                        row.update({"model": model_spec["name"], "repeat": rep, "rule_set": rule_set_name,
                                    "include_rules": m["include_rules"], "guarded": m["guarded"], "activation": m["activation"]})
                        rows_f.write(json.dumps(row) + "\n")
                        rows_f.flush()
                        done.add(key)
                        print(f"{model_spec['name']:>10s} {mode} {sc.scenario_id} r{rep}: success={row['success']:.0f} "
                              f"exec_viol={row['executed_violations']:.0f} tokens={row['tokens']:.0f} "
                              f"[{time.time() - started:6.0f}s]", flush=True)

    rows = [json.loads(l) for l in rows_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    write_csv(rows, out / "episodes.csv")
    aggs = aggregate(rows, ("model", "mode"))
    (out / "table_llm.md").write_text(markdown_table(aggs, TABLE_COLUMNS, ("model", "mode")) + "\n", encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(manifest({
        "config": cfg, "modes": modes, "repeats": repeats, "temperature": temperature, "n_scenarios": len(scenarios),
        "n_episodes": len(rows), "mode_definitions": MODES,
    }), indent=1), encoding="utf-8")
    print((out / "table_llm.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
