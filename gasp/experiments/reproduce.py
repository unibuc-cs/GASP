"""One command for every deterministic table in the paper.

    python -m gasp.experiments.reproduce --out outputs/paper --per-family 20 --seed 2027

Writes: scenarios.json, feature_table.json, per-episode metrics CSV, traces
(JSONL), aggregate tables (markdown + LaTeX), rule-set and overseer
sensitivity tables, GAU weight grid, role-ablation table, manifest.json.
LLM runs are a separate script (run_grid.py) because they cost money.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from gasp.core.env import EnvConfig
from gasp.core.metrics import AGG_COLUMNS, aggregate, gau_weight_grid, markdown_table, write_csv
from gasp.core.rules import RuleSet
from gasp.domains import get_domain
from gasp.domains.smartcity import feature_table
from gasp.experiments.ablation import role_ablation
from gasp.experiments.common import make_scenarios, manifest, metrics_rows, run_mode, save_scenarios
from gasp.policies import make_policy


MAIN_COLUMNS = ["success", "steps", "proposals", "attempted_violations", "executed_violations", "missed_approvals",
                "overseer_load", "tsc", "false_alert", "hidden_harm", "silent_violation_rate", "gau"]

# activation, brain, guard  -> mode label.  Names mirror the LLM modes M0-M4.
DETERMINISTIC_MODES = [
    ("direct", "direct_naive", False, "D0-direct-naive-noguard"),
    ("direct", "direct_naive", True, "D0g-direct-naive-guard"),
    ("all", "naive", False, "D1-all-naive-noguard"),
    ("all", "naive", True, "D1g-all-naive-guard"),
    ("scenario", "naive", False, "D2-roles-naive-noguard"),
    ("scenario", "naive", True, "D3-roles-naive-guard"),
    ("scenario", "procedural", False, "D4-roles-procedural-noguard"),
    ("scenario", "procedural", True, "D5-roles-procedural-guard"),
    ("direct", "direct_procedural", False, "D6-direct-procedural-noguard"),
    ("direct", "direct_procedural", True, "D6g-direct-procedural-guard"),
]


def latex_table(aggs: List[Dict[str, Any]], columns: List[str]) -> str:
    header = {"success": "Succ.", "steps": "Steps", "proposals": "Prop.", "attempted_violations": "Att. viol.",
              "executed_violations": "Exec. viol.", "missed_approvals": "Miss. appr.", "overseer_load": "Overseer",
              "tsc": "TSC", "false_alert": "False alert", "hidden_harm": "Hidden harm", "silent_violation_rate": "Silent viol.", "gau": "GAU"}
    lines = [r"\begin{tabular}{l" + "c" * len(columns) + "}", r"\toprule",
             r"\textbf{Mode} & " + " & ".join(r"\textbf{" + header.get(c, c) + "}" for c in columns) + r" \\", r"\midrule"]
    for a in aggs:
        cells = []
        for c in columns:
            v = a.get(c)
            cells.append("--" if v is None else f"{v:.2f}")
        lines.append(a["mode"].replace("-", " ") + " & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("outputs/paper"))
    ap.add_argument("--per-family", type=int, default=20)
    ap.add_argument("--seed", type=int, default=2027)
    ap.add_argument("--max-steps", type=int, default=16)
    ap.add_argument("--domain", default="smartcity")
    ap.add_argument("--no-traces", action="store_true")
    ap.add_argument("--skip-ablation", action="store_true")
    args = ap.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    domain = get_domain(args.domain)
    options = {"max_steps": args.max_steps}
    scenarios = make_scenarios(domain, args.per_family, args.seed, options)
    save_scenarios(scenarios, out / "scenarios.json")
    (out / "feature_table.json").write_text(json.dumps(feature_table(scenarios), indent=1), encoding="utf-8")

    trace_dir = None if args.no_traces else out / "traces"
    all_rows: List[Dict[str, Any]] = []

    # 1. Main deterministic grid at R2.
    rules = RuleSet.named("R2")
    for activation, brain, guarded, label in DETERMINISTIC_MODES:
        policy = make_policy(domain, rules, brain)
        cfg = EnvConfig(activation=activation, guarded=guarded, rule_set="R2", mode_name=label)
        results = run_mode(domain, scenarios, policy, cfg, rules, trace_dir)
        all_rows += metrics_rows(results, args.max_steps, {"rule_set": "R2", "overseer": "scenario", "policy": brain})
    main_rows = [r for r in all_rows if r["rule_set"] == "R2" and r["overseer"] == "scenario"]
    aggs = aggregate(main_rows, ("mode",))
    (out / "table_main.md").write_text(markdown_table(aggs, MAIN_COLUMNS) + "\n", encoding="utf-8")
    (out / "table_main.tex").write_text(latex_table(aggs, MAIN_COLUMNS) + "\n", encoding="utf-8")
    fam_aggs = aggregate(main_rows, ("mode", "family"))
    (out / "table_by_family.md").write_text(markdown_table(fam_aggs, MAIN_COLUMNS, ("mode", "family")) + "\n", encoding="utf-8")

    # 2. Rule-set sensitivity: the two informative modes under R1, R3.
    sens_modes = [m for m in DETERMINISTIC_MODES if m[3] in ("D2-roles-naive-noguard", "D3-roles-naive-guard",
                                                             "D4-roles-procedural-noguard", "D5-roles-procedural-guard")]
    for rs_name in ("R1", "R3"):
        rs = RuleSet.named(rs_name)
        for activation, brain, guarded, label in sens_modes:
            policy = make_policy(domain, rs, brain)
            cfg = EnvConfig(activation=activation, guarded=guarded, rule_set=rs_name, mode_name=label)
            results = run_mode(domain, scenarios, policy, cfg, rs, None)
            all_rows += metrics_rows(results, args.max_steps, {"rule_set": rs_name, "overseer": "scenario", "policy": brain})
    sens_rows = [r for r in all_rows if r["overseer"] == "scenario" and r["mode"] in {m[3] for m in sens_modes}]
    sens_aggs = aggregate(sens_rows, ("rule_set", "mode"))
    (out / "table_rulesets.md").write_text(markdown_table(sens_aggs, MAIN_COLUMNS, ("rule_set", "mode")) + "\n", encoding="utf-8")

    # 3. Overseer availability sweep (forced on/off) for the informative modes, under R2 and R3.
    for rs_name in ("R2", "R3"):
        rs = RuleSet.named(rs_name)
        for avail in (True, False):
            for activation, brain, guarded, label in sens_modes:
                policy = make_policy(domain, rs, brain)
                cfg = EnvConfig(activation=activation, guarded=guarded, rule_set=rs_name, mode_name=label, overseer_available=avail)
                results = run_mode(domain, scenarios, policy, cfg, rs, None)
                all_rows += metrics_rows(results, args.max_steps, {"rule_set": rs_name, "overseer": "always" if avail else "never", "policy": brain})
    ov_rows = [r for r in all_rows if r["mode"] in {m[3] for m in sens_modes} and r["overseer"] != "scenario"]
    ov_aggs = aggregate(ov_rows, ("rule_set", "overseer", "mode"))
    (out / "table_overseer.md").write_text(markdown_table(ov_aggs, MAIN_COLUMNS + ["approvals_granted", "approvals_denied"], ("rule_set", "overseer", "mode")) + "\n", encoding="utf-8")

    # 4. Per-episode CSV (everything) and GAU weight grid on the main rows.
    write_csv(all_rows, out / "episodes.csv")
    grid = gau_weight_grid(main_rows, max_steps=args.max_steps)
    first = Counter(g["ranking"][0] for g in grid)
    (out / "gau_weight_grid.json").write_text(json.dumps({"first_place_counts": dict(first), "grid": grid}, indent=1), encoding="utf-8")

    # 5. Role ablation (RDC) for the roles-based modes at R2.
    if not args.skip_ablation:
        abl = role_ablation(domain, scenarios, rules, [m for m in DETERMINISTIC_MODES if m[0] == "scenario"], args.max_steps)
        (out / "role_ablation.json").write_text(json.dumps(abl, indent=1), encoding="utf-8")

    (out / "manifest.json").write_text(json.dumps(manifest({
        "per_family": args.per_family, "seed": args.seed, "max_steps": args.max_steps, "domain": args.domain,
        "modes": [m[3] for m in DETERMINISTIC_MODES], "rule_sets": ["R1", "R2", "R3"],
        "n_episodes": len(all_rows),
    }), indent=1), encoding="utf-8")

    print((out / "table_main.md").read_text(encoding="utf-8"))
    print("GAU first place counts over the weight grid:", dict(first))


if __name__ == "__main__":
    main()
