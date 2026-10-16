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

from collections import Counter

from gasp.core.metrics import aggregate, gau_weight_grid
from gasp.experiments.analyze import read_rows


MAIN_COLUMNS = [("success", "Succ."), ("steps", "Steps"), ("attempted_violations", "Att. viol."), ("executed_violations", "Exec. viol."),
                ("overseer_load", "Overseer"), ("tsc", "TSC"), ("hallucinated_refs", "Halluc."), ("false_alert", "False alert"),
                ("hidden_harm", "Hidden harm"), ("silent_violation_rate", "Silent viol."), ("formatting_failures", "Format fail."),
                ("tokens", "Tokens"), ("gau", "GAU")]

STATS_METRICS = [("executed_violations", "executed violations"), ("attempted_violations", "attempted violations"),
                 ("false_alert", "false alert"), ("hidden_harm", "hidden harm"), ("success", "success"), ("steps", "steps"),
                 ("overseer_load", "overseer load"), ("hallucinated_refs", "hallucinated refs")]

DISPLAY = {"glimmer": "Glimmer 30B", "gptoss120b": "gpt-oss-120b", "gemma4": "Gemma 4 E4B", "qwen122b": "Qwen3.5-122B", "gemma4nt": "Gemma 4 E4B, no reasoning",
           "sol": "GPT-6 Sol", "luna": "GPT-6 Luna"}


def display(model: str) -> str:
    """The model's name as the paper writes it; unknown names are printed as they are."""
    return DISPLAY.get(model, model)


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
        lines.append(f"{display(model)} & {a['mode']} ({MODE_DESC.get(a['mode'], '')}) & " + " & ".join(fmt(a.get(c)) for c, _ in MAIN_COLUMNS) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


COMPACT_METRICS = [("executed_violations", "Exec. viol."), ("attempted_violations", "Att. viol."), ("success", "Succ."),
                   ("steps", "Steps"), ("overseer_load", "Overseer"), ("tokens", "Tokens")]
PAIR_ORDER = ["M2:M3", "M2:M4", "M3:M4"]          # the table shows the three primary pairs; M0:M3 and M1:M2 are quoted in the text


def stars(p) -> str:
    if p is None:
        return ""
    return "$^{***}$" if p < 0.001 else "$^{**}$" if p < 0.01 else "$^{*}$" if p < 0.05 else ""


def stats_table(stats: List[Dict[str, Any]]) -> str:
    """One row per model and comparison: mean paired difference (second mode minus first), Holm-corrected Wilcoxon p as stars.
    Intervals and Cliff's delta stay in outputs/llm/stats/paired_stats.md."""
    by_pair: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for r in stats:
        by_pair[(r["group"], r["pair"])][r["metric"]] = r
    lines = [r"\begin{tabular}{ll" + "r" * len(COMPACT_METRICS) + "}", r"\toprule",
             r"\textbf{Model} & \textbf{Pair} & " + " & ".join(r"\textbf{" + h + "}" for _, h in COMPACT_METRICS) + r" \\", r"\midrule"]
    groups = sorted({g for g, _ in by_pair})
    for gi, group in enumerate(groups):
        pairs = [p for p in PAIR_ORDER if (group, p) in by_pair]
        for k, pair in enumerate(pairs):
            a, b = pair.split(":")
            metrics = by_pair[(group, pair)]
            cells = []
            for key, _ in COMPACT_METRICS:
                r = metrics.get(key)
                if r is None:
                    cells.append("--")
                    continue
                d = r["mean_diff"]
                txt = f"{d / 1000:+.1f}k" if key == "tokens" else f"{d:+.2f}".replace("-0.00", "+0.00")
                cells.append(txt + stars(r.get("p_holm")))
            lines.append(f"{display(group) if k == 0 else ''} & {b} $-$ {a} & " + " & ".join(cells) + r" \\")
        if gi < len(groups) - 1:
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"

SENS_COLUMNS = [("success", "Succ."), ("steps", "Steps"), ("attempted_violations", "Att. viol."), ("executed_violations", "Exec. viol."),
                ("overseer_load", "Overseer"), ("approvals_denied", "Denied"), ("false_alert", "False alert"), ("hidden_harm", "Hidden harm")]
TAG_DESC = {"R1": "R1 (lenient)", "R3": "R3 (strict)", "ov-always": "R2, human always available", "ov-never": "R2, human never available"}


def sens_table(rows: List[Dict[str, Any]]) -> str:
    """Sensitivity sweeps: one block per model and sweep tag, M2 and M3 rows."""
    aggs = aggregate(rows, ("model", "tag", "mode"))
    lines = [r"\begin{tabular}{lll" + "c" * len(SENS_COLUMNS) + "}", r"\toprule",
             r"\textbf{Model} & \textbf{Setting} & \textbf{Mode} & " + " & ".join(r"\textbf{" + h + "}" for _, h in SENS_COLUMNS) + r" \\", r"\midrule"]
    last = None
    for a in aggs:
        key = (a["model"], a["tag"])
        model = a["model"] if key != last and (last is None or a["model"] != last[0]) else ""
        tag = TAG_DESC.get(str(a["tag"]), str(a["tag"])) if key != last else ""
        if last is not None and key != last:
            lines.append(r"\midrule")
        last = key
        lines.append(f"{display(model)} & {tag} & {a['mode']} & " + " & ".join(fmt(a.get(c)) for c, _ in SENS_COLUMNS) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def macros(rows: List[Dict[str, Any]]) -> str:
    """Numbers used in the prose that change when rows are added: the GAU weight grid per model.
    Modes whose mean GAU is equal (for instance two modes with no violations and the same success when steps weigh
    nothing) share first place; the order sentence counts only settings without ties."""
    out = []
    for model in sorted({r["model"] for r in rows}):
        grid = gau_weight_grid([r for r in rows if r["model"] == model], max_steps=16)
        top_sets = []
        for g in grid:
            best_value = max(g["means"].values())
            top_sets.append({m for m, v in g["means"].items() if v >= best_value - 1e-9})
        first = Counter(m for t in top_sets for m in t)
        best, n = sorted(first.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        tied = sum(1 for t in top_sets if best in t and len(t) > 1)
        strict = [tuple(g["ranking"]) for g in grid if len({round(v, 9) for v in g["means"].values()}) == len(g["means"])]
        order = Counter(strict).most_common(1)[0] if strict else (tuple(), 0)
        name = "".join(ch for ch in model if ch.isalpha())
        text = f"{best} ranks first in {n} of {len(grid)} weight settings"
        if tied:
            others = sorted({m for t in top_sets if best in t for m in t} - {best})
            text += f" (in {tied} of them tied with {', '.join(others)})"
        if order[1]:
            text += "; the order " + ", ".join(order[0]) + f" holds in {order[1]} of them"
        out.append(f"\\newcommand{{\\gaugrid{name}}}{{{text}}}")
    return "\n".join(out) + "\n"

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=str, required=True)
    ap.add_argument("--stats", type=Path, default=None)
    ap.add_argument("--sens", type=str, default=None, help="glob of sensitivity-sweep episodes.csv files (rows carry a tag)")
    ap.add_argument("--dest", type=Path, default=Path("paper/tables"))
    ap.add_argument("--skip-tag", action="append", default=[], help="sweep tag to leave out of the sensitivity table")
    args = ap.parse_args()
    rows: List[Dict[str, Any]] = []
    for path in sorted(glob.glob(args.episodes)) or [args.episodes]:
        rows += read_rows(Path(path))
    args.dest.mkdir(parents=True, exist_ok=True)
    (args.dest / "table_llm_main.tex").write_text(main_table(rows), encoding="utf-8")
    (args.dest / "llm_macros.tex").write_text(macros(rows), encoding="utf-8")
    if args.stats and args.stats.exists():
        stats = json.loads(args.stats.read_text(encoding="utf-8"))
        (args.dest / "table_llm_stats.tex").write_text(stats_table(stats), encoding="utf-8")
    if args.sens:
        srows: List[Dict[str, Any]] = []
        for path in sorted(glob.glob(args.sens)):
            srows += read_rows(Path(path))
        srows = [r for r in srows if r.get("tag") not in args.skip_tag]
        if srows:
            (args.dest / "table_llm_sens.tex").write_text(sens_table(srows), encoding="utf-8")
    print("wrote", args.dest / "table_llm_main.tex", "llm_macros.tex", "(+ table_llm_stats.tex)" if args.stats else "",
          "(+ table_llm_sens.tex)" if args.sens else "")


if __name__ == "__main__":
    main()
