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
                 "overseer_load", "tsc", "hallucinated_refs", "false_alert", "hidden_harm", "silent_violation_rate", "brier",
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
    ap.add_argument("--estimate", action="store_true",
                    help="no API calls: run the grid with the procedural JSON backend and report calls and tokens")
    ap.add_argument("--rule-set", type=str, default=None, help="override the config's rule set (R1, R2, R3)")
    ap.add_argument("--overseer", choices=["scenario", "always", "never"], default="scenario",
                    help="force the overseer available or unavailable in every scenario (sensitivity runs)")
    ap.add_argument("--tag", type=str, default=None, help="label stored with every row (e.g. R3-never)")
    ap.add_argument("--shard", type=str, default=None,
                    help="K/N: run only every N-th scenario starting at K (0-based), to spread one mode over N processes "
                         "against a local server that batches requests; give each shard its own --out")
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    domain = get_domain(cfg.get("domain", "smartcity"))
    rule_set_name = args.rule_set or cfg.get("rule_set", "R2")
    rules = RuleSet.named(rule_set_name)
    overseer_override = {"scenario": None, "always": True, "never": False}[args.overseer]
    repeats = args.repeats or int(cfg.get("repeats", 5))
    temperature = float(cfg.get("temperature", 0.7))
    max_steps = int(cfg.get("max_steps", 16))
    modes = [m.strip() for m in (args.modes.split(",") if args.modes else cfg.get("modes", list(MODES)))]
    models = cfg["models"]
    if args.models:
        wanted = {m.strip() for m in args.models.split(",")}
        models = [m for m in models if m["name"] in wanted]
    if args.estimate:
        models = [{"name": "estimate", "kind": "procedural-json"}]

    scenarios = load_scenarios(args.scenarios)
    if args.limit:
        per_fam: Dict[str, int] = {}
        kept = []
        for sc in scenarios:
            if per_fam.get(sc.family, 0) < args.limit:
                kept.append(sc)
                per_fam[sc.family] = per_fam.get(sc.family, 0) + 1
        scenarios = kept
    if args.shard:
        k, n = (int(x) for x in args.shard.split("/"))
        if not 0 <= k < n:
            raise SystemExit(f"--shard {args.shard}: K must be between 0 and N-1")
        scenarios = scenarios[k::n]

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
    backend_notes: Dict[str, Any] = {}
    with rows_path.open("a", encoding="utf-8") as rows_f:
        for model_spec in models:
            backend = make_backend(model_spec, domain, rules)
            backend_notes[model_spec["name"]] = backend
            for mode in modes:
                m = MODES[mode]
                # A model entry may override the grid's temperature and the answer length (reasoning models
                # need room for their thinking before the JSON); both are recorded in the manifest's config.
                model_temperature = float(model_spec.get("temperature", temperature))
                policy = LLMRolePolicy(domain, backend, rules, include_rules=m["include_rules"], temperature=model_temperature,
                                       max_tokens=int(model_spec.get("max_tokens", 400)),
                                       cache_dir=(out / "cache") if model_temperature == 0 else None)
                env_cfg = EnvConfig(activation=m["activation"], guarded=m["guarded"], rule_set=rule_set_name,
                                    mode_name=mode, max_steps=max_steps, overseer_available=overseer_override)
                for sc in scenarios:
                    for rep in range(repeats):
                        key = (model_spec["name"], mode, sc.scenario_id, rep)
                        if key in done:
                            continue
                        res = run_episode(domain, sc, policy, env_cfg, rules)
                        write_jsonl(res.records, trace_dir / f"{model_spec['name']}__{mode}__{sc.scenario_id}__r{rep}.jsonl")
                        row = episode_metrics(res, max_steps)
                        row.update({"model": model_spec["name"], "repeat": rep, "rule_set": rule_set_name,
                                    "overseer": args.overseer, "tag": args.tag or "",
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
    prompt_hashes = {}
    for role in list(domain.role_actions):
        for include in (True, False):
            from gasp.policies.llm import system_prompt
            import hashlib
            prompt_hashes[f"{role}:{'rules' if include else 'norules'}"] = hashlib.sha256(
                system_prompt(domain, role, rules, include).encode("utf-8")).hexdigest()[:16]
    (out / "manifest.json").write_text(json.dumps(manifest({
        "config": cfg, "modes": modes, "repeats": repeats, "temperature": temperature, "n_scenarios": len(scenarios),
        "shard": args.shard,
        "n_episodes": len(rows), "mode_definitions": MODES, "system_prompt_hashes": prompt_hashes,
        "backend_adaptations": {name: getattr(b, "adaptations", []) for name, b in backend_notes.items()},
    }), indent=1), encoding="utf-8")
    print((out / "table_llm.md").read_text(encoding="utf-8"))
    if args.estimate:
        tokens = sum(r["tokens"] for r in rows)
        calls = sum(r["calls"] for r in rows)
        print(f"ESTIMATE for {len(rows)} episodes: {calls} model calls, about {tokens / 1e6:.1f}M tokens (input + output, "
              f"chars/4) with a perfectly compliant policy. Budget about 1.5x of that for a real model (retries, longer "
              f"episodes), times the number of repeats you run.")


if __name__ == "__main__":
    main()
