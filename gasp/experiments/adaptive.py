"""Trust-adaptive governor: overseer load against hidden harm.

    python -m gasp.experiments.adaptive --out outputs/paper/adaptive --per-family 20 --seed 2027

Static guard: every soft approval goes to the human.  Adaptive governor with
threshold t: a role whose trust is at or above t skips soft approvals.  Trust
grows with supported, compliant actions and drops with attempted violations.
Hard approvals (road closures that block hospital access) are never waived.

The overseer knows things the rules do not encode: in a share of scenarios
(hidden_denial_rate) the human would deny the soft request, and an action
executed without asking then causes hidden harm.  So the experiment measures
what autonomy earned by compliance costs when compliance is not the risk.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from gasp.core.env import EnvConfig
from gasp.core.metrics import aggregate, markdown_table, write_csv
from gasp.core.rules import RuleSet
from gasp.domains import get_domain
from gasp.experiments.common import make_scenarios, metrics_rows, run_mode
from gasp.policies import make_policy


THRESHOLDS: List[Optional[float]] = [None, 0.9, 0.7, 0.5, 0.3, 0.0]   # None = static guard
COLUMNS = ["success", "steps", "overseer_load", "approvals_waived", "hidden_harm", "hidden_exposure", "executed_violations", "gau"]

SERIES_COLORS = {"procedural": "#2a78d6", "naive": "#eb6834"}   # fixed categorical slots 1 and 2


def label(th: Optional[float]) -> str:
    return "static" if th is None else f"t={th:.1f}"


def run(domain, scenarios, rules: RuleSet, brain: str, th: Optional[float], max_steps: int) -> List[Dict[str, Any]]:
    policy = make_policy(domain, rules, brain)
    cfg = EnvConfig(activation="scenario", guarded=True, rule_set=rules.id, mode_name=f"{brain}-{label(th)}",
                    adaptive_threshold=th)
    results = run_mode(domain, scenarios, policy, cfg, rules, None)
    return metrics_rows(results, max_steps, {"brain": brain, "threshold": label(th), "rule_set": rules.id})


def plot(aggs: List[Dict[str, Any]], out: Path, rule_set: str, rate: float) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.2, 3.0), dpi=200)
    for i, brain in enumerate(("procedural", "naive")):
        pts = [a for a in aggs if a["brain"] == brain]
        pts.sort(key=lambda a: -a["overseer_load"])
        xs = [a["overseer_load"] for a in pts]
        ys = [a["hidden_harm"] for a in pts]
        ax.plot(xs, ys, "-", color=SERIES_COLORS[brain], linewidth=2, marker="o", markersize=5, label=brain)
        # Label the two ends only; the intermediate thresholds sit on the line (listed in the caption).
        for a, x, y in zip(pts, xs, ys):
            if a["threshold"] in ("static", "t=0.0"):
                txt = "static guard" if a["threshold"] == "static" else "all soft approvals delegated"
                ax.annotate(txt, (x, y), textcoords="offset points", xytext=(6, -12 - 9 * i) if a["threshold"] == "static" else (6, 4 - 9 * i),
                            fontsize=6, color=SERIES_COLORS[brain])
    ax.set_xlabel("approval requests per episode (overseer load)")
    ax.set_ylabel("episodes with hidden harm")
    ax.set_title(f"{rule_set}, hidden context in {int(rate * 100)}% of scenarios", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(True, color="#eeeeee", linewidth=0.6)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("outputs/paper/adaptive"))
    ap.add_argument("--per-family", type=int, default=20)
    ap.add_argument("--seed", type=int, default=2027)
    ap.add_argument("--max-steps", type=int, default=16)
    ap.add_argument("--rates", type=str, default="0.05,0.15,0.30")
    ap.add_argument("--rule-sets", type=str, default="R2,R3")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    domain = get_domain("smartcity")

    all_rows: List[Dict[str, Any]] = []
    tables = []
    for rs_name in args.rule_sets.split(","):
        rules = RuleSet.named(rs_name)
        for rate in [float(r) for r in args.rates.split(",")]:
            scenarios = make_scenarios(domain, args.per_family, args.seed, {"max_steps": args.max_steps, "hidden_denial_rate": rate})
            rows: List[Dict[str, Any]] = []
            for brain in ("procedural", "naive"):
                for th in THRESHOLDS:
                    rows += run(domain, scenarios, rules, brain, th, args.max_steps)
            for r in rows:
                r["hidden_rate"] = rate
            all_rows += rows
            aggs = aggregate(rows, ("brain", "threshold"))
            for a in aggs:
                a["rule_set"], a["hidden_rate"] = rs_name, rate
            tables.append(f"### {rs_name}, hidden context rate {rate}\n\n" + markdown_table(aggs, COLUMNS, ("brain", "threshold")) + "\n")
            plot(aggs, args.out / f"tradeoff_{rs_name}_{int(rate * 100):02d}.png", rs_name, rate)
    (args.out / "table_adaptive.md").write_text("\n".join(tables), encoding="utf-8")
    write_csv(all_rows, args.out / "episodes_adaptive.csv")
    print("\n".join(tables))


if __name__ == "__main__":
    main()
