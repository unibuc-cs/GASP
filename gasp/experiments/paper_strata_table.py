"""Where the leak and the cost sit: executed violations with the rules in the prompts (M2) and the guard's cost in steps
(M3) per incident family and per evidence quality, one pair of columns per model.

    python -m gasp.experiments.paper_strata_table --episodes "outputs/llm/*/episodes.csv" \
        --scenarios outputs/paper/scenarios.json --dest paper/tables --skip gemma4nt --skip gemma4rp --skip qwen122brp

The evidence quality comes from the scenario file (episodes.csv carries the family only). Models named with --skip (the
controls) are left out; models without M2 and M3 rows are left out as well.
"""

from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from gasp.experiments.analyze import read_rows
from gasp.experiments.paper_llm_tables import display

FAMILY_LABEL = {"traffic_accident": "traffic accident", "power_outage": "power outage", "flooded_underpass": "flooded underpass",
                "pollution_spike": "pollution spike"}
FAMILY_ORDER = ["traffic_accident", "power_outage", "flooded_underpass", "pollution_spike"]
EVIDENCE_ORDER = ["complete", "partial", "missing", "conflicting"]


def mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def strata_table(rows: List[Dict[str, Any]], quality: Dict[str, str], models: List[str]) -> str:
    # scenario means first (repeats averaged), then the stratum mean, as in every other table
    per_scenario: Dict[tuple, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        per_scenario[(r["model"], r["mode"], r["scenario_id"])]["executed_violations"].append(float(r["executed_violations"]))
        per_scenario[(r["model"], r["mode"], r["scenario_id"])]["steps"].append(float(r["steps"]))
        per_scenario[(r["model"], r["mode"], r["scenario_id"])]["family"] = r["family"]

    def cell(model: str, mode: str, metric: str, key: str, value: str) -> str:
        vals = []
        for (m, md, sid), d in per_scenario.items():
            if m != model or md != mode:
                continue
            stratum = d["family"] if key == "family" else quality.get(sid)
            if stratum == value:
                vals.append(mean(d[metric]))
        return f"{mean(vals):.2f}" if vals else "--"

    cols = "l" + "cc" * len(models)
    lines = [r"\begin{tabular}{" + cols + "}", r"\toprule",
             r"\textbf{Stratum} & " + " & ".join(r"\multicolumn{2}{c}{\textbf{" + display(m) + "}}" for m in models) + r" \\",
             " & " + " & ".join(r"M2 exec. & M3 steps" for _ in models) + r" \\", r"\midrule"]
    for fam in FAMILY_ORDER:
        cells = []
        for m in models:
            cells += [cell(m, "M2", "executed_violations", "family", fam), cell(m, "M3", "steps", "family", fam)]
        lines.append(FAMILY_LABEL.get(fam, fam) + " & " + " & ".join(cells) + r" \\")
    lines.append(r"\midrule")
    for q in EVIDENCE_ORDER:
        cells = []
        for m in models:
            cells += [cell(m, "M2", "executed_violations", "quality", q), cell(m, "M3", "steps", "quality", q)]
        lines.append(f"evidence {q} & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=str, default="outputs/llm/*/episodes.csv")
    ap.add_argument("--scenarios", type=Path, default=Path("outputs/paper/scenarios.json"))
    ap.add_argument("--dest", type=Path, default=Path("paper/tables"))
    ap.add_argument("--skip", action="append", default=[], help="model name to leave out (controls)")
    args = ap.parse_args()
    rows: List[Dict[str, Any]] = []
    for path in sorted(glob.glob(args.episodes)):
        rows += read_rows(Path(path))
    rows = [r for r in rows if r["model"] not in args.skip]
    quality = {s["scenario_id"]: s["evidence_quality"] for s in json.loads(args.scenarios.read_text(encoding="utf-8"))}
    modes_by_model: Dict[str, set] = defaultdict(set)
    for r in rows:
        modes_by_model[r["model"]].add(r["mode"])
    models = sorted((m for m, ms in modes_by_model.items() if {"M2", "M3"} <= ms), key=lambda m: display(m).lower())
    if not models:
        print("no model with M2 and M3 rows; strata table not written")
        return
    args.dest.mkdir(parents=True, exist_ok=True)
    out = args.dest / "table_strata.tex"
    out.write_text(strata_table(rows, quality, models), encoding="utf-8")
    print("wrote", out, "for", ", ".join(models))


if __name__ == "__main__":
    main()
