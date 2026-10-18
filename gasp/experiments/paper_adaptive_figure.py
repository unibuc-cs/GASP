"""The trust-adaptive trade-off figure (overseer load against hidden harm): the two deterministic policies from
outputs/paper/adaptive, plus one line per LLM model that ran the adaptive sweep (scripts/run_local_ablation.sh adaptive),
whose static point is the model's R3 M3 sweep.

    python -m gasp.experiments.paper_adaptive_figure --out paper/figures/tradeoff_R3_15.png
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from gasp.experiments.paper_llm_tables import display

COLORS = {"procedural": "#2a78d6", "naive": "#eb6834"}
LLM_COLORS = ["#2a9d5c", "#8e44ad", "#b8860b"]


def read(path: str) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def point(rows: List[Dict[str, str]]) -> Dict[str, float]:
    """Scenario means first, then the mean over scenarios."""
    per: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        for k in ("overseer_load", "hidden_harm", "success"):
            per[r["scenario_id"]][k].append(float(r[k]))
    out = {}
    for k in ("overseer_load", "hidden_harm", "success"):
        means = [sum(v[k]) / len(v[k]) for v in per.values()]
        out[k] = sum(means) / len(means) if means else float("nan")
    out["n"] = len(per)
    return out


def deterministic_series(path: Path, rule_set: str, rate: str) -> Dict[str, List[Dict[str, Any]]]:
    rows = [r for r in read(str(path)) if r["rule_set"] == rule_set and r["hidden_rate"] == rate]
    series: Dict[str, List[Dict[str, Any]]] = {}
    for brain in ("procedural", "naive"):
        pts = []
        for th in ("static", "t=0.9", "t=0.7", "t=0.5", "t=0.3", "t=0.0"):
            sel = [r for r in rows if r["brain"] == brain and r["threshold"] == th]
            if sel:
                pts.append({"label": th, **point(sel)})
        series[brain] = pts
    return series


def llm_series(sens_glob: str, rule_set: str = "R3") -> Dict[str, List[Dict[str, Any]]]:
    """One series per model: its R3 M3 sweep as the static guard, then every adaptive-t<th> run, by falling threshold."""
    by_model: Dict[str, Dict[str, List[Dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for d in sorted(glob.glob(sens_glob)):
        p = os.path.join(d, "episodes.csv")
        if not os.path.exists(p):
            continue
        for r in read(p):
            if r.get("mode") != "M3" or r.get("rule_set") != rule_set:
                continue
            tag = r.get("tag", "")
            if tag.startswith("adaptive-t"):
                by_model[r["model"]]["t=" + tag[len("adaptive-t"):]].append(r)
            elif tag == rule_set:
                by_model[r["model"]]["static"].append(r)
    series = {}
    for model, groups in by_model.items():
        if not any(k.startswith("t=") for k in groups):
            continue
        pts = [{"label": "static", **point(groups["static"])}] if "static" in groups else []
        for th in sorted((k for k in groups if k.startswith("t=")), key=lambda k: -float(k[2:])):
            pts.append({"label": th, **point(groups[th])})
        series[display(model) + " (M3)"] = pts
    return series


def plot(det: Dict[str, List[Dict[str, Any]]], llm: Dict[str, List[Dict[str, Any]]], out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.2, 3.0), dpi=200)
    all_series = [(k, v, COLORS[k]) for k, v in det.items()] + [(k, v, LLM_COLORS[i % len(LLM_COLORS)]) for i, (k, v) in enumerate(llm.items())]
    for i, (name, pts, color) in enumerate(all_series):
        xs = [p["overseer_load"] for p in pts]
        ys = [p["hidden_harm"] for p in pts]
        ax.plot(xs, ys, "-", color=color, linewidth=2, marker="o", markersize=5, label=name)
        for p, x, y in zip(pts, xs, ys):
            if p["label"] in ("static", "t=0.0"):
                txt = "static guard" if p["label"] == "static" else "all soft approvals delegated"
                ax.annotate(txt, (x, y), textcoords="offset points", ha="right" if p["label"] == "static" else "left",
                            xytext=(-6, 4 + 8 * i) if p["label"] == "static" else (6, 4 - 9 * i), fontsize=6, color=color)
    ax.set_xlabel("approval requests per episode (overseer load)")
    ax.set_ylabel("episodes with hidden harm")
    ax.set_title("R3, hidden context in 15% of scenarios", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(True, color="#eeeeee", linewidth=0.6)
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deterministic", type=Path, default=Path("outputs/paper/adaptive/episodes_adaptive.csv"))
    ap.add_argument("--sens", type=str, default="outputs/llm_sens/*", help="glob of sweep run directories")
    ap.add_argument("--out", type=Path, default=Path("paper/figures/tradeoff_R3_15.png"))
    args = ap.parse_args()
    det = deterministic_series(args.deterministic, "R3", "0.15")
    llm = llm_series(args.sens)
    plot(det, llm, args.out)
    for name, pts in list(det.items()) + list(llm.items()):
        print(name + ": " + "; ".join(f"{p['label']} load {p['overseer_load']:.2f} harm {p['hidden_harm']:.2f} succ {p['success']:.2f} (n={p['n']})" for p in pts))
    print("wrote", args.out, "with" if llm else "without", "LLM series")


if __name__ == "__main__":
    main()
