"""Where the prompt leaks and what the guard blocks, rule by rule: a LaTeX table from the trace files.

    python -m gasp.experiments.paper_rule_table --runs "outputs/llm/*" --dest paper/tables

For every model found in the runs' episodes.csv files, two columns: executed violations per incident in M2 (rules in the
prompts, no guard) and blocked attempts per incident in M3 (guard, rules not in the prompts), one row per rule of the
active rule set. Reads the trace records (`rule_id`, `executed_violation`, `attempted_violation`), so it needs the traces
of M2 and M3 for every model that ran both modes; when such a model's traces are missing the table is left as it is, so that a partial copy of
the results (for instance a workspace without the trace files) cannot overwrite a complete table.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

RULES = [("scope", "scope"), ("memory_provenance", "memory provenance"), ("public_comm", "public communication"),
         ("evidence", "evidence"), ("approval", "approval"), ("pollution_zone", "pollution zone")]
DISPLAY = {"glimmer": "Glimmer 30B", "gptoss120b": "gpt-oss-120b", "gemma4": "Gemma 4 E4B", "qwen122b": "Qwen3.5-122B", "gemma4nt": "Gemma 4 E4B, no reasoning",
           "gemma4rp": "Gemma 4 E4B, reinforced prompt", "qwen122brp": "Qwen3.5-122B, reinforced prompt",
           "sol": "GPT-6 Sol", "luna": "GPT-6 Luna"}


def scan(run_dirs, modes=("M2", "M3")):
    """Per (model, mode): episodes with a trace file, executed violations and blocked attempts by rule."""
    episodes = Counter()
    executed = defaultdict(Counter)
    blocked = defaultdict(Counter)
    for d in run_dirs:
        for f in glob.glob(os.path.join(d, "traces", "*.jsonl")):
            name = os.path.basename(f)
            parts = name[:-6].split("__")
            if len(parts) < 4 or parts[1] not in modes:
                continue
            model, mode = parts[0], parts[1]
            episodes[(model, mode)] += 1
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    if r.get("executed_violation"):
                        executed[(model, mode)][r.get("rule_id")] += 1
                    elif r.get("attempted_violation"):
                        blocked[(model, mode)][r.get("rule_id")] += 1
    return episodes, executed, blocked


def models_in_tables(run_dirs, modes=("M2", "M3")):
    """Models whose episode tables cover every mode the table needs; a control run with M2 only is left out."""
    seen = defaultdict(set)
    for d in run_dirs:
        p = os.path.join(d, "episodes.csv")
        if os.path.exists(p):
            with open(p, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    seen[row["model"]].add(row["mode"])
    return {m for m, ms in seen.items() if set(modes) <= ms}


def table(models, episodes, executed, blocked) -> str:
    cols = "l" + "cc" * len(models)
    lines = [r"\begin{tabular}{" + cols + "}", r"\toprule",
             r"\textbf{Rule} & " + " & ".join(r"\multicolumn{2}{c}{\textbf{" + DISPLAY.get(m, m) + "}}" for m in models) + r" \\",
             " & " + " & ".join(r"M2 exec. & M3 blocked" for _ in models) + r" \\", r"\midrule"]
    for rid, label in RULES:
        cells = []
        for m in models:
            n2, n3 = episodes[(m, "M2")], episodes[(m, "M3")]
            cells.append(f"{executed[(m, 'M2')][rid] / n2:.2f}" if n2 else "--")
            cells.append(f"{blocked[(m, 'M3')][rid] / n3:.2f}" if n3 else "--")
        lines.append(label + " & " + " & ".join(cells) + r" \\")
    lines.append(r"\midrule")
    cells = []
    for m in models:
        n2, n3 = episodes[(m, "M2")], episodes[(m, "M3")]
        cells.append(f"{sum(executed[(m, 'M2')].values()) / n2:.2f}" if n2 else "--")
        cells.append(f"{sum(blocked[(m, 'M3')].values()) / n3:.2f}" if n3 else "--")
    lines.append(r"all rules & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="outputs/llm/*", help="glob of run directories")
    ap.add_argument("--dest", type=Path, default=Path("paper/tables"))
    ap.add_argument("--allow-partial", action="store_true", help="write the table even if some model has no traces")
    args = ap.parse_args()
    run_dirs = sorted(glob.glob(args.runs))
    episodes, executed, blocked = scan(run_dirs)
    wanted = models_in_tables(run_dirs)
    have = {m for (m, mode), n in episodes.items() if n and mode == "M2"} & {m for (m, mode), n in episodes.items() if n and mode == "M3"}
    missing = sorted(wanted - have)
    if missing and not args.allow_partial:
        print(f"rule table not written: no M2 and M3 traces for {', '.join(missing)}; the existing table is kept")
        return
    models = sorted(have, key=lambda m: DISPLAY.get(m, m).lower())
    args.dest.mkdir(parents=True, exist_ok=True)
    out = args.dest / "table_rule_leak.tex"
    out.write_text(table(models, episodes, executed, blocked), encoding="utf-8")
    print("wrote", out, "for", ", ".join(models))


if __name__ == "__main__":
    main()
