"""LaTeX tables for the LLM results: model x mode means, and the paired comparisons.

    python -m gasp.experiments.paper_llm_tables --episodes "outputs/llm/*/episodes.csv" \
        --stats outputs/llm/stats/paired_stats.json --dest paper/tables

Writes table_llm_main.tex (one row per model and mode) and table_llm_stats.tex (M2 vs M3, M0 vs M3,
M3 vs M4 per model: mean difference with its interval, Cliff's delta, Holm-adjusted p) for the metrics that
carry RQ1 to RQ3.  Run analyze.py first for the stats file.
"""

from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from gasp.core.metrics import aggregate
from gasp.experiments.analyze import read_rows


MAIN_COLUMNS = [("success", "Succ."), ("steps", "Steps"), ("attempted_violations", "Att. viol."), ("executed_violations", "Exec. viol."),
                ("overseer_load", "Overseer"), ("tsc", "TSC"), ("hallucinated_refs", "Halluc."), ("false_alert", "False alert"),
                ("hidden_harm", "Hidden harm"), ("silent_violation_rate", "Silent viol."), ("formatting_failures", "Format fail."),
                ("tokens", "Tokens"), ("gau", "GAU")]

STATS_METRICS = [("executed_violations", "executed violations"), ("attempted_violations", "attempted violations"),
                 ("false_alert", "false alert"), ("hidden_harm", "hidden harm"), ("success", "success"), ("steps", "steps"),
                 ("overseer_load", "overseer load"), ("hallucinated_refs", "hallucinated refs")]

MODE_DESC = {"M0": "one agent, rules in prompt", "M0g": "one agent, rules, guard", "M1": "roles, no rules", "M2": "roles, rules in prompts",
             "M3": "roles, guard", "M4": "roles, rules and guard"}


def fmt(v, digits=2):
    if v is None:
        return "--"
    if abs(v) >= 1000:
        return f"{v / 1000:.1f}k"
    return f"{v:.{digits}f}"


def main_table(rows: List[Dict[str, Any]]) -> str:
    aggs = aggregate(rows, ("model", "mode"))
    lines = [r"\begin{tabular}{ll" + "c" * len(MAIN_COLUMNS) + "}", r"\toprule",
             r"\textbf{Model} & \textbf{Mode} & " + " & ".join(r"\textbf{" + h + "}" for _, h in MAIN_COLUMNS) + r" \\", r"\midrule"]
    last_model = None
    for a in aggs:
        model = a["model"] if a["model"] != last_model else ""
        if last_model is not None and model:
            lines.append(r"\midrule")
        last_model = a["model"]
        lines.append(f"{model} & {a['mode']} ({MODE_DESC.get(a['mode'], '')}) & " + " & ".join(fmt(a.get(c)) for c, _ in MAIN_COLUMNS) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def stats_table(stats: List[Dict[str, Any]]) -> str:
    by_pair: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for r in stats:
        by_pair[(r["group"], r["pair"])][r["metric"]] = r
    lines = [r"\begin{tabular}{llrrr}", r"\toprule",
             r"\textbf{Model, comparison} & \textbf{Metric} & \textbf{Difference [95\% CI]} & \textbf{Cliff's $\delta$} & \textbf{$p$ (Holm)} \\", r"\midrule"]
    for (group, pair), metrics in sorted(by_pair.items()):
        a, b = pair.split(":")
        first = True
        for key, label in STATS_METRICS:
            r = metrics.get(key)
            if r is None:
                continue
            head = f"{group}, {b} vs {a}" if first else ""
            first = False
            ci = r["ci_diff"]
            p = r.get("p_holm")
            p_txt = "--" if p is None else (r"$<$0.001" if p < 0.001 else f"{p:.3f}")
            lines.append(f"{head} & {label} & {r['mean_diff']:+.2f} [{ci[0]:.2f}, {ci[1]:.2f}] & {r['cliffs_delta']:+.2f} & {p_txt} \\\\")
        lines.append(r"\midrule")
    if lines[-1] == r"\midrule":
        lines.pop()
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=str, required=True)
    ap.add_argument("--stats", type=Path, default=None)
    ap.add_argument("--dest", type=Path, default=Path("paper/tables"))
    args = ap.parse_args()
    rows: List[Dict[str, Any]] = []
    for path in sorted(glob.glob(args.episodes)) or [args.episodes]:
        rows += read_rows(Path(path))
    args.dest.mkdir(parents=True, exist_ok=True)
    (args.dest / "table_llm_main.tex").write_text(main_table(rows), encoding="utf-8")
    if args.stats and args.stats.exists():
        stats = json.loads(args.stats.read_text(encoding="utf-8"))
        (args.dest / "table_llm_stats.tex").write_text(stats_table(stats), encoding="utf-8")
    print("wrote", args.dest / "table_llm_main.tex", "(+ table_llm_stats.tex)" if args.stats else "")


if __name__ == "__main__":
    main()
